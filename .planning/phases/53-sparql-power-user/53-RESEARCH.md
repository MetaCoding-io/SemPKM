# Phase 53: SPARQL Power User - Research

**Researched:** 2026-03-10
**Domain:** SPARQL console interface, CodeMirror 6 editor, server-side query persistence, ontology-aware autocomplete, IRI pill rendering
**Confidence:** HIGH

## Summary

Phase 53 replaces the existing Yasgui-based SPARQL console with a custom-built interface using CodeMirror 6 as a new bottom-panel tab in the workspace. The implementation spans four domains: (1) CodeMirror 6 SPARQL editor with syntax highlighting via `codemirror-lang-sparql` and custom autocompletion, (2) server-side query history and saved queries via new SQLAlchemy models + Alembic migration + FastAPI CRUD endpoints, (3) IRI pill rendering via backend batch label+type resolution using existing LabelService and IconService, and (4) a vocabulary API endpoint that extracts classes and predicates from installed Mental Model ontology graphs for the autocomplete data source.

The project already has a working CM6 integration pattern in `editor.js` (ESM imports from esm.sh CDN with unpinned `@6` ranges), a complete SPARQL execution pipeline in `sparql/router.py` + `sparql/client.py`, role gating (`_enforce_sparql_role`), IRI detection logic in `sparql.html` (`isSemPKMObjectIri`), batch label resolution (`LabelService.resolve_batch`), type icon lookup (`IconService.get_type_icon`), and an established bottom-panel tab system in `workspace.js`. The workspace template shows 4 existing tabs (Event Log, Inference, AI Copilot, Lint) -- the SPARQL tab becomes the 5th.

**Primary recommendation:** Build this in waves -- (1) DB models + migration + CRUD endpoints, (2) SPARQL panel UI with CM6 editor + execution + result table, (3) IRI pill enrichment, (4) ontology autocomplete. Each wave is independently testable.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **Replace Yasgui entirely** with a custom-built SPARQL interface using CodeMirror 6 (already used for the Markdown body editor in `editor.js`)
- **Single location:** workspace bottom panel, new SPARQL tab alongside Event Log, Inference, etc.
- **Remove the admin `/admin/sparql` page** -- the sidebar nav link should point to the workspace with the SPARQL panel auto-opened
- **Role gating carries forward from Phase 52:** guest has no SPARQL tab, member queries current graph only, owner has full access
- **Hybrid side-by-side + cell history layout:** top section: editor on the left, current results table on the right (side-by-side split); bottom section: scrollable cell history showing previous query+result pairs from this session
- **Cell history is session-only** -- cleared on page reload. Server-side history (dropdown) is the persistent record
- **Toolbar above editor:** Run, Save, History dropdown, Saved dropdown buttons
- **Server-side persistence** -- every query execution saves to server-side history (replaces Yasgui's localStorage-only approach)
- **Auto-save on every execution** -- duplicate consecutive queries are deduplicated (only timestamp updates)
- **History dropdown** in toolbar shows recent queries with relative timestamp + first-line preview
- **100 most recent** queries kept per user, older entries pruned automatically
- **Separate toolbar dropdown** from history (two distinct buttons: History and Saved)
- **Save button** in toolbar prompts for name + optional description, saves current editor query
- **Star from history** -- each history dropdown entry has a star icon; clicking it prompts for a name and promotes it to saved
- **IRI Pill Design: Icon + label chip** -- compact rounded chip with type icon on left, resolved label on right
- **Object IRIs only** -- only SemPKM objects get pill treatment. Vocabulary IRIs render as compact QNames in plain text
- **Backend batch resolve** -- after query execution, backend collects unique object IRIs from results, batch-resolves labels+types via LabelService, returns enriched result data
- **Click opens workspace tab** -- clicking a pill calls `openTab(iri, label)`, standard workspace behavior
- **Hover shows full IRI** as tooltip
- **Always-on (aggressive) autocomplete** -- suggestions appear as the user types any token
- **Full SPARQL awareness** -- suggests PREFIX declarations, classes, predicates from installed Mental Models, SPARQL keywords, and previously-used variable names
- **Type badges in dropdown** -- each suggestion shows a badge: C for class, P for predicate, D for datatype, K for keyword
- **API endpoint, cached client-side** -- new endpoint returns all prefixes, classes, and predicates from installed Mental Models. Editor fetches once on load, caches in memory

### Claude's Discretion
- Exact CodeMirror 6 SPARQL language package choice (e.g., `codemirror-lang-sparql` or custom grammar)
- Split ratio between editor and results panes
- Cell history expansion animation and styling
- How to detect model changes for autocomplete cache invalidation
- Result table styling (borders, row hover, column widths)
- Keyboard shortcut for running queries (Ctrl+Enter is standard)

### Deferred Ideas (OUT OF SCOPE)
- **AI Query Helper** -- LLM-generated SPARQL from natural language description. Separate phase.
- **Query sharing** -- Phase 54 (SPARQL Advanced)
- **Promoted queries as nav tree views** -- Phase 54 (SPARQL Advanced)
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| SPARQL-02 | User's SPARQL query history is persisted server-side and accessible across devices | New SQLAlchemy model `SparqlQueryHistory` + Alembic migration 007 + CRUD endpoints on sparql router. Uses existing auth `get_current_user` DI for user scoping. |
| SPARQL-03 | User can save a SPARQL query with a name and description | New SQLAlchemy model `SavedSparqlQuery` + same migration + separate CRUD endpoints. Star-from-history promotes history entry to saved query. |
| SPARQL-05 | SPARQL result IRIs display as labeled pills with type icons that open in workspace tabs | Backend enrichment: after query execution, collect IRIs from results, call `LabelService.resolve_batch()` + `IconService.get_type_icon()`, return enriched JSON. Frontend renders pills with `openTab(iri, label)` onclick. Port `isSemPKMObjectIri` logic from `sparql.html`. |
| SPARQL-06 | SPARQL editor provides ontology-aware autocomplete for prefixes, classes, and predicates from installed models | New `GET /api/sparql/vocabulary` endpoint queries model ontology graphs for `owl:Class`, `owl:ObjectProperty`, `owl:DatatypeProperty` entities. CM6 `autocompletion({ override: [sparqlCompletions] })` with custom completion source. |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| CodeMirror 6 | @6 (unpinned) | SPARQL editor | Already in codebase for Markdown editing; esm.sh CDN pattern established |
| codemirror-lang-sparql | 2.0.0 | SPARQL syntax highlighting | Lezer-based grammar for SPARQL 1.1; MIT licensed; CM6-native |
| @codemirror/autocomplete | @6 (unpinned) | Custom autocompletion | CM6's official autocomplete extension; included in basicSetup |
| SQLAlchemy | 2.0.46+ | Query history/saved queries ORM models | Already used for all auth models; async support |
| Alembic | 1.18+ | Database migration for new tables | Already used; 6 migrations exist |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| LabelService | existing | Batch IRI label resolution | After query execution to resolve result IRIs to labels |
| IconService | existing | Type icon lookup | Render type icons in IRI pills |
| PrefixRegistry | existing | QName compaction | Compact vocabulary IRIs to QNames in result display |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| codemirror-lang-sparql | Custom Lezer grammar | More control but significant effort; existing package covers SPARQL 1.1 well |
| Server-side history | localStorage history | User decision locks server-side; localStorage was Yasgui's approach and is device-bound |
| Backend IRI enrichment | Frontend IRI resolution | User decision locks backend batch resolve; prevents frontend flicker |

**Installation:**
No npm/pip install needed for frontend (CDN via esm.sh). Backend already has all dependencies.

**CDN imports (new for this phase):**
```javascript
// SPARQL language support
import { sparql } from "https://esm.sh/codemirror-lang-sparql@2";
// Autocomplete (already bundled with basicSetup, but need explicit import for override)
import { autocompletion } from "https://esm.sh/@codemirror/autocomplete@6";
```

## Architecture Patterns

### Recommended Project Structure
```
backend/app/
  sparql/
    __init__.py          # existing
    client.py            # existing - prefix injection, graph scoping
    router.py            # MODIFIED - add history/saved/vocabulary CRUD endpoints
    models.py            # NEW - SparqlQueryHistory, SavedSparqlQuery SQLAlchemy models
    schemas.py           # NEW - Pydantic request/response schemas
  templates/browser/
    workspace.html       # MODIFIED - add SPARQL tab button (conditionally hidden for guests)
    sparql_panel.html    # NEW - SPARQL panel HTML template
frontend/static/
  js/
    sparql-console.js    # NEW - CM6 SPARQL editor, cell history, toolbar, result rendering
  css/
    workspace.css        # MODIFIED - add SPARQL panel styles (or new sparql.css)
backend/migrations/versions/
    007_sparql_tables.py # NEW - create sparql_query_history and saved_sparql_queries tables
```

### Pattern 1: Bottom Panel Tab Registration
**What:** Add SPARQL as a new bottom panel tab following the existing Event Log / Inference / AI Copilot / Lint pattern.
**When to use:** Adding the SPARQL tab button and pane.
**Example:**
```html
<!-- In workspace.html panel-tab-bar, conditionally shown based on role -->
{% if user.role != 'guest' %}
<button class="panel-tab" data-panel="sparql">SPARQL</button>
{% endif %}

<!-- Panel pane -->
<div class="panel-pane" id="panel-sparql">
  {% include 'browser/sparql_panel.html' %}
</div>
```

**Integration with workspace.js:**
```javascript
// In _applyPanelState(), add lazy-load for SPARQL tab:
if (panelState.open && panelState.activeTab === 'sparql') {
  // Initialize CM6 editor on first activation (lazy-load pattern)
  if (!window._sparqlEditorInit) {
    import('/js/sparql-console.js').then(function(mod) {
      mod.initSparqlConsole();
      window._sparqlEditorInit = true;
    });
  }
}
```

### Pattern 2: CodeMirror 6 ESM Import (Established Pattern)
**What:** Load CM6 via esm.sh CDN with unpinned @6 major version ranges.
**When to use:** All CM6 imports for the SPARQL editor.
**Example:**
```javascript
// From existing editor.js pattern -- use unpinned @6 to avoid state version conflicts
import { EditorView, keymap } from "https://esm.sh/@codemirror/view@6";
import { EditorState, Compartment } from "https://esm.sh/@codemirror/state@6";
import { basicSetup } from "https://esm.sh/codemirror@6.0.1";
import { sparql } from "https://esm.sh/codemirror-lang-sparql@2";
import { autocompletion } from "https://esm.sh/@codemirror/autocomplete@6";
```

### Pattern 3: SQLAlchemy User-Scoped Models
**What:** New DB models with user_id foreign keys, following existing patterns from auth/models.py.
**When to use:** SparqlQueryHistory and SavedSparqlQuery tables.
**Example:**
```python
class SparqlQueryHistory(Base):
    __tablename__ = "sparql_query_history"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    query_text: Mapped[str] = mapped_column(Text(), nullable=False)
    executed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

class SavedSparqlQuery(Base):
    __tablename__ = "saved_sparql_queries"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text(), nullable=True)
    query_text: Mapped[str] = mapped_column(Text(), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
```

### Pattern 4: SPARQL Result Enrichment (Backend Batch Resolve)
**What:** After query execution, scan result bindings for object IRIs, batch-resolve labels and types, return enriched JSON.
**When to use:** The `/api/sparql` POST endpoint needs modification or a new enriched endpoint.
**Example:**
```python
# In the enriched SPARQL endpoint
async def _enrich_sparql_results(raw_results: dict, label_service, icon_service, prefix_registry, base_namespace: str) -> dict:
    """Scan results for object IRIs, batch-resolve labels+types, add metadata."""
    bindings = raw_results.get("results", {}).get("bindings", [])

    # Collect unique URIs that are SemPKM object IRIs
    object_iris = set()
    for binding in bindings:
        for var_name, val in binding.items():
            if val.get("type") == "uri":
                uri = val["value"]
                if _is_object_iri(uri, base_namespace):
                    object_iris.add(uri)

    # Batch resolve labels
    labels = await label_service.resolve_batch(list(object_iris)) if object_iris else {}

    # Resolve types for each IRI (need separate SPARQL query)
    type_map = await _batch_resolve_types(client, list(object_iris)) if object_iris else {}

    # Attach enrichment metadata to response
    raw_results["_enrichment"] = {
        iri: {
            "label": labels.get(iri, iri),
            "type_iri": type_map.get(iri, ""),
            "icon": icon_service.get_type_icon(type_map.get(iri, ""), "tab"),
            "qname": prefix_registry.compact(iri),
        }
        for iri in object_iris
    }
    return raw_results
```

### Pattern 5: Vocabulary API for Autocomplete
**What:** New endpoint extracts classes and predicates from installed model ontology graphs.
**When to use:** Providing autocomplete data to the SPARQL editor.
**Example:**
```python
@router.get("/sparql/vocabulary")
async def get_sparql_vocabulary(
    user: User = Depends(get_current_user),
    client: TriplestoreClient = Depends(get_triplestore_client),
    prefix_registry: PrefixRegistry = Depends(get_prefix_registry),
) -> JSONResponse:
    """Return classes, predicates, and prefixes from installed Mental Models."""
    _enforce_sparql_role(user, "", False)  # Reject guests

    # Query ontology graphs for classes and properties
    query = """
    SELECT DISTINCT ?entity ?type ?label ?graph WHERE {
      GRAPH ?graph {
        ?entity a ?type .
        FILTER(?type IN (owl:Class, owl:ObjectProperty, owl:DatatypeProperty))
        OPTIONAL { ?entity rdfs:label ?label }
      }
      FILTER(STRSTARTS(STR(?graph), "urn:sempkm:model:") && STRENDS(STR(?graph), ":ontology"))
    }
    """
    results = await client.query(query)

    # Format for autocomplete: [{label, qname, type_badge, full_iri}]
    prefixes = prefix_registry.get_all_prefixes()
    # ... format and return
```

### Pattern 6: Custom CM6 Autocompletion Source
**What:** Register a custom completion source with the CM6 autocompletion extension.
**When to use:** Providing ontology-aware SPARQL autocomplete.
**Example:**
```javascript
// Custom completion source for SPARQL
function sparqlCompletions(context) {
  // Match word characters, colons (for prefixed names), and ? (for variables)
  var word = context.matchBefore(/[\w:?]*/);
  if (!word || (word.from === word.to && !context.explicit)) return null;

  var text = word.text;
  var options = [];

  // SPARQL keywords
  if (text.toUpperCase() === text || /^[A-Z]/.test(text)) {
    SPARQL_KEYWORDS.forEach(function(kw) {
      options.push({ label: kw, type: "keyword", detail: "K" });
    });
  }

  // Prefixed names (after a colon)
  if (text.indexOf(':') > 0) {
    var prefix = text.split(':')[0];
    // Filter vocabulary items matching this prefix
    vocabCache.filter(function(v) { return v.prefix === prefix; })
      .forEach(function(v) {
        options.push({
          label: v.qname,
          type: v.badge === 'C' ? 'class' : 'property',
          detail: v.badge
        });
      });
  }

  // PREFIX declarations
  if (/^[Pp]/.test(text)) {
    Object.entries(prefixCache).forEach(function([prefix, ns]) {
      options.push({
        label: 'PREFIX ' + prefix + ': <' + ns + '>',
        type: 'keyword',
        detail: 'D',
        apply: 'PREFIX ' + prefix + ': <' + ns + '>\n'
      });
    });
  }

  return { from: word.from, options: options, validFor: /^[\w:?]*$/ };
}
```

### Anti-Patterns to Avoid
- **Loading CM6 eagerly on workspace init:** The editor is heavy. Lazy-load via dynamic `import()` only when the SPARQL tab is first activated.
- **Using localStorage for query history:** User decision explicitly requires server-side persistence.
- **Frontend IRI resolution after rendering:** User decision requires backend batch resolve to avoid flicker.
- **Bundling CM6 with npm/esbuild:** Project uses CDN-only pattern (esm.sh). No build step.
- **Creating a separate SPARQL page:** All SPARQL UI goes in the workspace bottom panel.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| SPARQL syntax highlighting | Custom tokenizer/regex highlighting | `codemirror-lang-sparql` (Lezer grammar) | SPARQL 1.1 grammar is complex; Lezer parser gives proper AST |
| IRI label resolution | Custom SPARQL label queries | `LabelService.resolve_batch()` | Already handles precedence chain, caching, language prefs |
| IRI type detection | Custom type detection | `IconService.get_type_icon()` | Already parses model manifests, handles fallbacks |
| Prefix compaction | Custom namespace splitting | `PrefixRegistry.compact()` | Handles 3-layer precedence, reverse map caching |
| Object IRI detection | New detection logic | Port `isSemPKMObjectIri()` from `sparql.html` | Already has KNOWN_VOCAB_PREFIXES list, base_namespace check |
| Query role enforcement | New role checks | `_enforce_sparql_role()` from `sparql/router.py` | Already handles guest/member/owner differentiation |
| CM6 theme switching | New theme management | Existing `themeCompartment` pattern from `editor.js` | Dark/light mode switching already solved |

**Key insight:** The codebase already has all the service-layer building blocks. This phase is primarily UI construction (CM6 editor + panel layout) and CRUD plumbing (history/saved queries). The "hard" parts (label resolution, icon mapping, prefix expansion, role gating) are already implemented and tested.

## Common Pitfalls

### Pitfall 1: esm.sh Version Conflicts with CM6 Packages
**What goes wrong:** Pinning specific CM6 package versions (e.g., `@codemirror/view@6.35.1`) causes esm.sh to resolve different `@codemirror/state` versions for different packages, breaking the shared state singleton.
**Why it happens:** CM6 packages share a state module that must be the same instance. esm.sh resolves each import independently.
**How to avoid:** Use unpinned major version ranges (`@6`) exactly as `editor.js` does. Never pin patch versions for CM6 packages on esm.sh.
**Warning signs:** "Unrecognized extension value" errors, editor failing to initialize, state-related crashes.

### Pitfall 2: Bottom Panel Tab State Persistence Conflicts
**What goes wrong:** Adding a new panel tab that isn't in the existing `panelState.activeTab` options can cause `_applyPanelState()` to fail finding the active pane, leaving all panes hidden.
**Why it happens:** `panelState` is persisted in localStorage with `activeTab: 'sparql'`, but on page load, the `#panel-sparql` DOM element may not exist yet if the panel template hasn't loaded.
**How to avoid:** The panel HTML must be in the initial workspace.html render (not lazy-loaded via htmx). Only the CM6 editor initialization should be lazy. The `_applyPanelState` function already uses `document.getElementById('panel-' + panelState.activeTab)` which safely returns null for missing elements.
**Warning signs:** Panel stuck closed after selecting SPARQL tab, panel state resets.

### Pitfall 3: Alembic Migration Numbering
**What goes wrong:** Migration revision ID collision with concurrent development.
**Why it happens:** Latest migration is `006_indieauth_tables.py` with `down_revision = "005"`. New migration must be `007` with `down_revision = "006"`.
**How to avoid:** Check the latest migration file before creating a new one. Use the simple sequential numbering scheme (007, 008, etc.) already established.
**Warning signs:** Alembic error "Can't locate revision identified by '006'" or "Multiple head revisions".

### Pitfall 4: Guest Role Tab Visibility
**What goes wrong:** Guest users see the SPARQL tab but get 403 errors when trying to use it.
**Why it happens:** The tab button is rendered in the template without role-gating.
**How to avoid:** Conditionally render the SPARQL tab button in workspace.html using Jinja2: `{% if user.role != 'guest' %}`. The `user` variable is already available in the workspace template context from `browser/router.py`.
**Warning signs:** Guests seeing SPARQL tab, 403 errors in console.

### Pitfall 5: Lucide Icons in Flex Button Containers
**What goes wrong:** Toolbar button icons disappear (0px width).
**Why it happens:** Lucide SVGs inside flex containers without `flex-shrink: 0` get compressed.
**How to avoid:** Follow CLAUDE.md rule: size Lucide icons via CSS, add `flex-shrink: 0` on SVG inside flex parents. Reference implementation: `.panel-btn svg` in workspace.css.
**Warning signs:** Invisible toolbar icons, buttons appear empty.

### Pitfall 6: Large SPARQL Result Sets Blocking UI
**What goes wrong:** Rendering 1000+ result rows with IRI pills causes the browser to freeze.
**Why it happens:** Each pill requires DOM construction with event listeners, icon rendering, tooltip setup.
**How to avoid:** Limit result display to first 100-200 rows with a "Load more" pattern, or use virtual scrolling. Backend should return enrichment data but frontend should render incrementally.
**Warning signs:** Browser tab becoming unresponsive after query execution.

### Pitfall 7: Duplicate History Deduplication Logic
**What goes wrong:** Identical consecutive queries create separate history entries.
**Why it happens:** The requirement says "duplicate consecutive queries are deduplicated (only timestamp updates)" but the naive implementation compares query strings without normalizing whitespace.
**How to avoid:** Strip and normalize whitespace before comparison. Compare the stripped query text of the most recent entry for that user.
**Warning signs:** History dropdown showing many copies of the same query.

## Code Examples

### Existing CM6 Initialization Pattern (from editor.js)
```javascript
// Source: frontend/static/js/editor.js
import { EditorView, keymap } from "https://esm.sh/@codemirror/view@6";
import { EditorState, Compartment } from "https://esm.sh/@codemirror/state@6";
import { basicSetup } from "https://esm.sh/codemirror@6.0.1";

var themeCompartment = new Compartment();
var view = new EditorView({
  state: EditorState.create({
    doc: initialContent || '',
    extensions: [
      basicSetup,
      // language extension goes here (markdown() for editor.js, sparql() for SPARQL)
      themeCompartment.of(getCurrentTheme()),
      keymap.of([{ key: 'Mod-Enter', run: executeQuery }]),
    ]
  }),
  parent: container
});
```

### Existing SPARQL Execution Pipeline (from sparql/router.py)
```python
# Source: backend/app/sparql/router.py
# Role gating + prefix injection + graph scoping already implemented
_enforce_sparql_role(user, query, all_graphs)
processed = inject_prefixes(query)
processed = scope_to_current_graph(processed, all_graphs=all_graphs)
result = await client.query(processed)
```

### Existing IRI Detection (from admin/sparql.html)
```javascript
// Source: backend/app/templates/admin/sparql.html
var KNOWN_VOCAB_PREFIXES = [
  'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
  'http://www.w3.org/2000/01/rdf-schema#',
  'http://www.w3.org/2002/07/owl#',
  'http://purl.org/dc/terms/',
  // ... more standard vocab namespaces
  'urn:sempkm:'
];

function isSemPKMObjectIri(uri) {
  if (!uri) return false;
  var base = window.SEMPKM_BASE_NAMESPACE;
  if (base && uri.indexOf(base) === 0) return true;
  if (uri.indexOf('https://') !== 0) return false;
  for (var i = 0; i < KNOWN_VOCAB_PREFIXES.length; i++) {
    if (uri.indexOf(KNOWN_VOCAB_PREFIXES[i]) === 0) return false;
  }
  return true;
}
```

### Existing Panel Tab System (from workspace.js)
```javascript
// Source: frontend/static/js/workspace.js
var panelState = { open: false, height: 30, activeTab: 'event-log', maximized: false };

function initPanelTabs() {
  document.querySelectorAll('.panel-tab').forEach(function (btn) {
    btn.addEventListener('click', function () {
      panelState.activeTab = btn.dataset.panel;
      savePanelState();
      _applyPanelState();
      // Lazy-load content for specific tabs
    });
  });
}
```

### Existing Batch Label Resolution (from services/labels.py)
```python
# Source: backend/app/services/labels.py
results = await label_service.resolve_batch(list_of_iris)
# Returns: {iri: label_string, ...}
```

### Model Ontology Graph Query Pattern
```sparql
# Classes and properties from installed model ontology graphs
SELECT DISTINCT ?entity ?type ?label WHERE {
  GRAPH ?g {
    ?entity a ?type .
    FILTER(?type IN (
      <http://www.w3.org/2002/07/owl#Class>,
      <http://www.w3.org/2002/07/owl#ObjectProperty>,
      <http://www.w3.org/2002/07/owl#DatatypeProperty>
    ))
    OPTIONAL { ?entity rdfs:label ?label }
  }
  FILTER(STRSTARTS(STR(?g), "urn:sempkm:model:") && STRENDS(STR(?g), ":ontology"))
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Yasgui 4.5.0 (CDN, unpkg) | Custom CM6 SPARQL editor | Phase 53 | Full control over styling, behavior; matches SemPKM design language |
| localStorage query persistence | Server-side SQLAlchemy persistence | Phase 53 | Cross-device access, role-scoped, prunable |
| Frontend IRI link formatting | Backend batch enrichment | Phase 53 | No flicker, server-authoritative labels |
| No autocomplete | Ontology-aware CM6 autocomplete | Phase 53 | Power user productivity |

**Deprecated/outdated:**
- `@zazuko/yasgui@4.5.0`: Being removed entirely. All Yasgui CSS/JS imports in `sparql.html` will be deleted.
- `/admin/sparql` page: Being removed. Admin sidebar link should redirect to workspace with SPARQL panel open.
- `sparql-support` npm package: CodeMirror 5 addon, incompatible with CM6.

## Open Questions

1. **esm.sh resolution of codemirror-lang-sparql with CM6 @6**
   - What we know: The package is `codemirror-lang-sparql@2.0.0`, published Oct 2024. It targets CM6 but specific dependency version ranges are unclear.
   - What's unclear: Whether esm.sh correctly resolves its CM6 peer dependencies to match the `@6` ranges used by the existing editor.js imports.
   - Recommendation: Test the import `https://esm.sh/codemirror-lang-sparql@2` in a browser console first. If version conflicts arise, fall back to a simple syntax highlighter using CM6's `StreamLanguage` with a basic SPARQL tokenizer (keywords, URIs, prefixes, variables, strings, comments).

2. **Model change detection for autocomplete cache invalidation**
   - What we know: `IconService.invalidate()` exists and is called on model install/uninstall. No pub/sub or event bus for model changes.
   - What's unclear: Whether to poll, use a version counter, or check on each vocabulary fetch.
   - Recommendation: Add a simple `model_version` counter to app.state that increments on install/uninstall. The vocabulary endpoint returns it; the client caches alongside the counter and re-fetches when it changes. Simplest approach with zero overhead.

3. **Batch type resolution for IRI pills**
   - What we know: `LabelService.resolve_batch()` resolves labels. `IconService.get_type_icon(type_iri)` resolves icons per type. But there's no existing batch type resolution (getting `rdf:type` for many IRIs at once).
   - What's unclear: Whether to add a method to LabelService or create a separate query.
   - Recommendation: Add a `_batch_resolve_types()` helper in the sparql router that runs a single SPARQL VALUES query to get `rdf:type` for all object IRIs in results. Similar pattern to LabelService's batch query.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | Playwright 1.50.0 |
| Config file | e2e/playwright.config.ts |
| Quick run command | `cd /home/james/Code/SemPKM/e2e && npx playwright test --project=chromium tests/05-admin/` |
| Full suite command | `cd /home/james/Code/SemPKM/e2e && npx playwright test --project=chromium` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SPARQL-02 | Query history persists server-side | integration | Manual verification: execute query, reload, check history dropdown | No -- Wave 0 |
| SPARQL-03 | Save query with name and description | integration | Manual verification: save query, reload, check saved dropdown | No -- Wave 0 |
| SPARQL-05 | IRI pills with labels and type icons | smoke | Manual verification: execute query with object IRIs, verify pills render | No -- Wave 0 |
| SPARQL-06 | Ontology-aware autocomplete | smoke | Manual verification: type in editor, verify suggestions appear | No -- Wave 0 |

### Sampling Rate
- **Per task commit:** Manual smoke test in browser (execute query, check results)
- **Per wave merge:** Full E2E suite run
- **Phase gate:** Full suite green + manual SPARQL feature verification before `/gsd:verify-work`

### Wave 0 Gaps
- No existing SPARQL-specific E2E tests
- Manual testing is appropriate for this phase -- the SPARQL console is interactive/visual
- Backend API endpoints (history CRUD, vocabulary) could have pytest unit tests if desired
- Framework install: already available (`cd e2e && npx playwright test`)

## Sources

### Primary (HIGH confidence)
- `frontend/static/js/editor.js` - Established CM6 integration pattern (esm.sh CDN, theme compartment, cleanup)
- `backend/app/sparql/router.py` + `client.py` - Existing SPARQL execution pipeline, role gating
- `backend/app/services/labels.py` - LabelService.resolve_batch() API
- `backend/app/services/icons.py` - IconService.get_type_icon() API
- `backend/app/services/prefixes.py` - PrefixRegistry.compact() and get_all_prefixes()
- `backend/app/auth/models.py` - SQLAlchemy model patterns (User, UserSession, UserSetting)
- `backend/app/templates/admin/sparql.html` - isSemPKMObjectIri() detection logic
- `backend/app/templates/browser/workspace.html` - Panel tab bar structure
- `frontend/static/js/workspace.js` - panelState, _applyPanelState, initPanelTabs patterns

### Secondary (MEDIUM confidence)
- [codemirror-lang-sparql GitHub](https://github.com/aatauil/codemirror-lang-sparql) - v2.0.0, Lezer-based SPARQL grammar, MIT license
- [CodeMirror Autocompletion Example](https://codemirror.net/examples/autocompletion/) - CompletionContext API, custom completion source pattern
- [CodeMirror Autocomplete GitHub](https://github.com/codemirror/autocomplete) - addToOptions, override, type badges

### Tertiary (LOW confidence)
- esm.sh compatibility of codemirror-lang-sparql with @6 ranges -- needs browser verification

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All backend libraries already in use; CM6 pattern established; codemirror-lang-sparql verified on GitHub
- Architecture: HIGH - All patterns follow existing codebase conventions; panel tab system, service injection, SQLAlchemy models all have precedent
- Pitfalls: HIGH - esm.sh version conflicts documented from editor.js experience; panel state persistence is well-understood
- Autocomplete: MEDIUM - CM6 autocomplete API is well-documented but custom SPARQL completion source is novel code; codemirror-lang-sparql esm.sh compatibility unverified

**Research date:** 2026-03-10
**Valid until:** 2026-04-10 (stable domain, no fast-moving dependencies)
