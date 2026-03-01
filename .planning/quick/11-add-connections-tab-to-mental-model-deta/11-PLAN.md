---
phase: quick-11
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - backend/app/services/models.py
  - backend/app/admin/router.py
  - backend/app/templates/admin/model_detail.html
  - frontend/static/css/style.css
autonomous: true
requirements: [QUICK-11]

must_haves:
  truths:
    - "Model detail page shows a tabbed interface (Schema / Connections)"
    - "Connections tab loads via htmx lazy-load on tab click, not on page load"
    - "Connections tab shows outbound and inbound triples grouped by predicate label"
    - "Each connection row shows the source/target label (clickable to open in browser) and a count badge per predicate group"
    - "Empty state shown when a model has no live instance connections"
  artifacts:
    - path: "backend/app/services/models.py"
      provides: "get_model_connections() method on ModelService"
      contains: "async def get_model_connections"
    - path: "backend/app/admin/router.py"
      provides: "GET /admin/models/{model_id}/connections htmx partial endpoint"
      contains: "async def admin_model_connections"
    - path: "backend/app/templates/admin/model_detail.html"
      provides: "Tab bar UI and Connections tab panel with htmx lazy-load"
      contains: "connections-tab"
    - path: "frontend/static/css/style.css"
      provides: "Tab bar and connections panel styling"
      contains: ".model-detail-tabs"
  key_links:
    - from: "backend/app/templates/admin/model_detail.html"
      to: "/admin/models/{model_id}/connections"
      via: "hx-get on connections tab click"
      pattern: "hx-get.*connections"
    - from: "backend/app/admin/router.py"
      to: "model_service.get_model_connections"
      via: "async method call"
      pattern: "get_model_connections"
    - from: "backend/app/services/models.py"
      to: "TriplestoreClient.query"
      via: "SPARQL SELECT with GRAPH <urn:sempkm:current>"
      pattern: "urn:sempkm:current"
---

<objective>
Add a "Connections" tab to the mental model detail dashboard (`/admin/models/{model_id}`) showing live SPARQL-queried triples for all instances of the model's types, grouped by predicate label and direction (outbound/inbound).

Purpose: The existing model detail page shows schema metadata (types, fields, relationships, views) and basic analytics (instance counts, top nodes). A Connections tab provides a live, aggregated view of how instances are actually connected in the knowledge graph -- bridging the gap between schema design and real data.

Output: Tabbed model detail page with Schema tab (existing content) and Connections tab (htmx lazy-loaded SPARQL results grouped by predicate/direction).
</objective>

<execution_context>
@/home/james/.claude/get-shit-done/workflows/execute-plan.md
@/home/james/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@backend/app/admin/router.py
@backend/app/services/models.py
@backend/app/templates/admin/model_detail.html
@backend/app/templates/browser/properties.html
@frontend/static/css/style.css

<interfaces>
<!-- Key types and contracts the executor needs. -->

From backend/app/admin/router.py:
```python
def templates_response(request: Request, template: str, context: dict, block_name: str | None = None):
    """Render a template with optional block-level rendering."""

def _is_htmx_request(request: Request) -> bool:
    """Check if the request is an htmx partial request."""

# Existing route pattern:
@router.get("/models/{model_id}")
async def admin_model_detail(request, model_id, user, model_service): ...
```

From backend/app/services/models.py:
```python
class ModelService:
    _client: TriplestoreClient  # injected in __init__

    async def get_model_detail(self, model_id: str) -> dict | None: ...
    async def get_type_analytics(self, type_iris: list[str]) -> dict[str, dict]: ...
    # _query_types returns: [{"iri": str, "local_name": str, "label": str, "comment": str}]
```

From backend/app/dependencies.py:
```python
async def get_model_service(request: Request) -> ModelService: ...
async def get_label_service(request: Request) -> LabelService: ...
```

From backend/app/services/labels.py:
```python
class LabelService:
    async def resolve_batch(self, iris: list[str]) -> dict[str, str]: ...
```

From backend/app/templates/browser/properties.html (pattern to follow for grouping):
```html
<!-- outbound_grouped: dict of predicate_label -> list of {iri, label} -->
<!-- inbound_grouped: dict of predicate_label -> list of {iri, label} -->
```
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add get_model_connections() to ModelService and connections endpoint to admin router</name>
  <files>
    backend/app/services/models.py
    backend/app/admin/router.py
  </files>
  <action>
**ModelService (backend/app/services/models.py):**

Add method `async def get_model_connections(self, model_id: str) -> dict | None` after `get_type_analytics()`. This method:

1. Calls `registry_list_models` to find the model, returns `None` if not found.
2. Gets type IRIs by calling `self._query_types(graphs.ontology, namespace)`.
3. Runs a single batched SPARQL query for outbound connections (all instances of all model types as subjects):

```sparql
SELECT ?subject ?subjectType ?predicate ?object WHERE {
  GRAPH <urn:sempkm:current> {
    ?subject a ?subjectType .
    ?subject ?predicate ?object .
    FILTER(isIRI(?object))
    FILTER(?predicate != <http://www.w3.org/1999/02/22-rdf-syntax-ns#type>)
  }
  VALUES ?subjectType { <type1> <type2> ... }
} LIMIT 500
```

4. Runs a single batched SPARQL query for inbound connections (all instances as objects):

```sparql
SELECT ?source ?predicate ?target ?targetType WHERE {
  GRAPH <urn:sempkm:current> {
    ?target a ?targetType .
    ?source ?predicate ?target .
    FILTER(isIRI(?source))
    FILTER(?predicate != <http://www.w3.org/1999/02/22-rdf-syntax-ns#type>)
  }
  VALUES ?targetType { <type1> <type2> ... }
} LIMIT 500
```

5. Collects all IRIs (subjects, objects, predicates, sources, targets) and calls `self._label_service.resolve_batch()` for labels. NOTE: `_label_service` does not exist on ModelService yet. Instead, accept `label_service: LabelService` as a parameter to `get_model_connections()` (same pattern as the browser router passes it separately).

6. Groups outbound by predicate label, each entry has `{iri, label, type_label}`. Groups inbound similarly. Returns:

```python
{
    "outbound_grouped": {"predicate_label": [{"iri": ..., "label": ..., "type_label": ...}, ...]},
    "inbound_grouped": {"predicate_label": [{"iri": ..., "label": ..., "type_label": ...}, ...]},
    "total_outbound": int,
    "total_inbound": int,
}
```

Wrap both SPARQL queries in try/except, logging warnings on failure (following existing service error handling pattern). Return empty groups on failure.

**Admin Router (backend/app/admin/router.py):**

Add a new endpoint after `admin_model_detail`:

```python
@router.get("/models/{model_id}/connections")
async def admin_model_connections(
    request: Request,
    model_id: str,
    user: User = Depends(require_role("owner")),
    model_service: ModelService = Depends(get_model_service),
    label_service: LabelService = Depends(get_label_service),
):
```

Add imports: `from app.dependencies import get_label_service` and `from app.services.labels import LabelService`.

This endpoint:
1. Calls `model_service.get_model_connections(model_id, label_service)`.
2. If `None`, returns a simple error partial.
3. Renders `admin/model_connections.html` as an htmx partial (always partial, no full-page fallback -- it's only loaded via htmx tab click).
4. Context: `request`, `connections` (the dict), `model_id`.
  </action>
  <verify>
    <automated>cd /home/james/Code/SemPKM && python -c "
import ast, sys
# Check ModelService has get_model_connections
with open('backend/app/services/models.py') as f:
    tree = ast.parse(f.read())
methods = [n.name for n in ast.walk(tree) if isinstance(n, ast.AsyncFunctionDef)]
assert 'get_model_connections' in methods, 'get_model_connections not found in models.py'

# Check router has admin_model_connections
with open('backend/app/admin/router.py') as f:
    tree = ast.parse(f.read())
funcs = [n.name for n in ast.walk(tree) if isinstance(n, ast.AsyncFunctionDef)]
assert 'admin_model_connections' in funcs, 'admin_model_connections not found in router.py'
print('OK: Both method and endpoint exist')
"</automated>
  </verify>
  <done>
    - ModelService.get_model_connections() queries outbound/inbound triples for all model type instances, groups by predicate label
    - GET /admin/models/{model_id}/connections renders htmx partial with grouped connections data
  </done>
</task>

<task type="auto">
  <name>Task 2: Add tab UI to model_detail.html, create connections partial template, and add CSS</name>
  <files>
    backend/app/templates/admin/model_detail.html
    backend/app/templates/admin/model_connections.html
    frontend/static/css/style.css
  </files>
  <action>
**model_detail.html modifications:**

After the Stats Bar div and before the "Types & Schema" detail-section, add a tab bar:

```html
<!-- Tab Bar -->
<div class="model-detail-tabs">
    <button class="model-tab active" data-tab="schema" onclick="switchModelTab('schema')">
        <i data-lucide="list"></i> Schema
    </button>
    <button class="model-tab" data-tab="connections" onclick="switchModelTab('connections')"
            hx-get="/admin/models/{{ detail.info.model_id }}/connections"
            hx-target="#connections-content"
            hx-swap="innerHTML"
            hx-trigger="click once">
        <i data-lucide="network"></i> Connections
    </button>
</div>
```

Wrap ALL existing content below the tab bar (Types & Schema section, Relationship Map section, Technical Details section) in a tab panel div:

```html
<div id="schema-panel" class="model-tab-panel active">
    <!-- existing Types & Schema, Relationship Map, Technical Details sections unchanged -->
</div>
<div id="connections-panel" class="model-tab-panel" style="display:none;">
    <div id="connections-content">
        <div class="connections-loading">
            <i data-lucide="loader-2" class="spin"></i> Loading connections...
        </div>
    </div>
</div>
```

Add `switchModelTab` JavaScript function in the existing `<script>` block at bottom:

```javascript
function switchModelTab(tabName) {
    // Update tab buttons
    document.querySelectorAll('.model-tab').forEach(function(btn) {
        btn.classList.toggle('active', btn.dataset.tab === tabName);
    });
    // Update panels
    document.getElementById('schema-panel').style.display = tabName === 'schema' ? '' : 'none';
    document.getElementById('connections-panel').style.display = tabName === 'connections' ? '' : 'none';
    // Re-init lucide icons after htmx swap
    if (typeof lucide !== 'undefined') lucide.createIcons();
}
```

**New template: backend/app/templates/admin/model_connections.html**

Create this as an htmx partial (no extends, no block -- just the content fragment):

```html
{# Connections tab content for model detail dashboard.
   Rendered as htmx partial loaded on tab click.
   Accepts:
     connections: dict with outbound_grouped, inbound_grouped, total_outbound, total_inbound
     model_id: str
#}

<div class="connections-panel-content">
    <div class="connections-summary">
        <span class="connections-stat">
            <i data-lucide="arrow-up-right"></i>
            <strong>{{ connections.total_outbound }}</strong> outbound
        </span>
        <span class="connections-stat">
            <i data-lucide="arrow-down-left"></i>
            <strong>{{ connections.total_inbound }}</strong> inbound
        </span>
    </div>

    {% if not connections.outbound_grouped and not connections.inbound_grouped %}
    <div class="connections-empty">
        <i data-lucide="unplug"></i>
        <p>No connections found. Create objects and link them to see connections here.</p>
    </div>
    {% else %}

    {% if connections.outbound_grouped %}
    <div class="connections-direction-section">
        <h3><i data-lucide="arrow-up-right"></i> Outbound</h3>
        {% for predicate, targets in connections.outbound_grouped.items() %}
        <div class="connection-group">
            <div class="connection-predicate">
                {{ predicate }} <span class="count-badge">{{ targets | length }}</span>
            </div>
            <div class="connection-items">
                {% for item in targets %}
                <a class="connection-item" href="/browser/workspace?iri={{ item.iri | urlencode }}"
                   hx-get="/browser/workspace?iri={{ item.iri | urlencode }}"
                   hx-target="#app-content" hx-swap="innerHTML" hx-push-url="true"
                   title="{{ item.iri }}">
                    <span class="connection-label">{{ item.label }}</span>
                    {% if item.type_label %}
                    <span class="connection-type-badge">{{ item.type_label }}</span>
                    {% endif %}
                </a>
                {% endfor %}
            </div>
        </div>
        {% endfor %}
    </div>
    {% endif %}

    {% if connections.inbound_grouped %}
    <div class="connections-direction-section">
        <h3><i data-lucide="arrow-down-left"></i> Inbound</h3>
        {% for predicate, sources in connections.inbound_grouped.items() %}
        <div class="connection-group">
            <div class="connection-predicate">
                {{ predicate }} <span class="count-badge">{{ sources | length }}</span>
            </div>
            <div class="connection-items">
                {% for item in sources %}
                <a class="connection-item" href="/browser/workspace?iri={{ item.iri | urlencode }}"
                   hx-get="/browser/workspace?iri={{ item.iri | urlencode }}"
                   hx-target="#app-content" hx-swap="innerHTML" hx-push-url="true"
                   title="{{ item.iri }}">
                    <span class="connection-label">{{ item.label }}</span>
                    {% if item.type_label %}
                    <span class="connection-type-badge">{{ item.type_label }}</span>
                    {% endif %}
                </a>
                {% endfor %}
            </div>
        </div>
        {% endfor %}
    </div>
    {% endif %}

    {% endif %}
</div>

<script>
if (typeof lucide !== 'undefined') lucide.createIcons();
</script>
```

**CSS additions (frontend/static/css/style.css):**

Add AFTER the existing Model Detail Dashboard section (after the analytics/placeholder styles, before the next major section). These styles implement the tab bar and connections panel:

```css
/* Model Detail Tabs */
.model-detail-tabs {
  display: flex;
  gap: 0;
  border-bottom: 2px solid var(--color-border);
  margin-bottom: 1.5rem;
}

.model-tab {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  padding: 0.6rem 1.1rem;
  background: none;
  border: none;
  border-bottom: 2px solid transparent;
  margin-bottom: -2px;
  font-size: 0.85rem;
  font-weight: 500;
  color: var(--color-text-muted);
  cursor: pointer;
  transition: color 0.15s, border-color 0.15s;
}

.model-tab i, .model-tab svg {
  width: 15px;
  height: 15px;
}

.model-tab:hover {
  color: var(--color-text);
}

.model-tab.active {
  color: var(--color-primary);
  border-bottom-color: var(--color-primary);
  font-weight: 600;
}

/* Connections panel */
.connections-summary {
  display: flex;
  gap: 1.5rem;
  margin-bottom: 1.25rem;
}

.connections-stat {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  font-size: 0.85rem;
  color: var(--color-text-muted);
}

.connections-stat i, .connections-stat svg {
  width: 14px;
  height: 14px;
}

.connections-stat strong {
  color: var(--color-text);
}

.connections-empty {
  text-align: center;
  padding: 2.5rem 1rem;
  color: var(--color-text-faint);
}

.connections-empty i, .connections-empty svg {
  width: 32px;
  height: 32px;
  margin-bottom: 0.5rem;
  opacity: 0.5;
}

.connections-empty p {
  font-size: 0.88rem;
  max-width: 400px;
  margin: 0 auto;
  line-height: 1.5;
}

.connections-direction-section {
  margin-bottom: 1.5rem;
}

.connections-direction-section > h3 {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  font-size: 0.9rem;
  font-weight: 600;
  color: var(--color-text);
  margin-bottom: 0.75rem;
}

.connections-direction-section > h3 i,
.connections-direction-section > h3 svg {
  width: 15px;
  height: 15px;
  color: var(--color-text-muted);
}

.connection-group {
  margin-bottom: 0.75rem;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  overflow: hidden;
}

.connection-predicate {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 0.75rem;
  background: var(--color-code-bg);
  font-size: 0.82rem;
  font-weight: 600;
  color: var(--color-text-muted);
  border-bottom: 1px solid var(--color-border);
}

.connection-items {
  display: flex;
  flex-direction: column;
}

.connection-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.4rem 0.75rem;
  font-size: 0.82rem;
  color: var(--color-text);
  text-decoration: none;
  border-bottom: 1px solid var(--color-border-subtle);
  transition: background 0.1s;
}

.connection-item:last-child {
  border-bottom: none;
}

.connection-item:hover {
  background: var(--color-surface-hover);
}

.connection-label {
  flex: 1;
}

.connection-type-badge {
  font-size: 0.7rem;
  font-family: var(--font-mono);
  color: var(--color-text-faint);
  background: var(--color-code-bg);
  padding: 0.1rem 0.4rem;
  border-radius: 3px;
  border: 1px solid var(--color-border);
}

.connections-loading {
  text-align: center;
  padding: 2rem;
  color: var(--color-text-faint);
  font-size: 0.85rem;
}

.connections-loading i, .connections-loading svg {
  width: 18px;
  height: 18px;
  margin-right: 0.3rem;
  vertical-align: middle;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.spin {
  animation: spin 1s linear infinite;
  display: inline-block;
}
```

NOTE: Check if a `@keyframes spin` already exists in style.css before adding. If it does, skip the duplicate keyframe definition and just use the existing `.spin` class (or add the `.spin` class if only the keyframe exists).
  </action>
  <verify>
    <automated>cd /home/james/Code/SemPKM && python -c "
import os, sys

# Check model_connections.html template exists
assert os.path.exists('backend/app/templates/admin/model_connections.html'), 'model_connections.html missing'

# Check model_detail.html has tab structure
with open('backend/app/templates/admin/model_detail.html') as f:
    content = f.read()
assert 'model-detail-tabs' in content, 'Tab bar not found in model_detail.html'
assert 'connections-panel' in content, 'Connections panel not found'
assert 'switchModelTab' in content, 'switchModelTab JS not found'
assert 'hx-get' in content and 'connections' in content, 'htmx lazy-load not wired'

# Check CSS has tab and connections styles
with open('frontend/static/css/style.css') as f:
    css = f.read()
assert '.model-detail-tabs' in css, 'Tab CSS missing'
assert '.connection-group' in css, 'Connection group CSS missing'

print('OK: Template, tabs, htmx wiring, and CSS all present')
"</automated>
  </verify>
  <done>
    - Model detail page has Schema/Connections tab bar
    - Connections tab lazy-loads via htmx on first click (hx-trigger="click once")
    - Connections partial template renders grouped outbound/inbound connections with clickable links to browser workspace
    - CSS styles tab bar, connection groups, loading state, and empty state
    - Lucide icons re-initialized after htmx swap
  </done>
</task>

</tasks>

<verification>
1. Navigate to `/admin/models/basic-pkm` (or any installed model)
2. Page loads with Schema tab active showing existing content
3. Click "Connections" tab -- loading spinner appears briefly, then connections content loads via htmx
4. Outbound section shows triples where model instances are subjects, grouped by predicate label
5. Inbound section shows triples where model instances are objects, grouped by predicate label
6. Each connection item is clickable and navigates to the browser workspace for that object
7. Count badges show number of connections per predicate group
8. Clicking Schema tab returns to original content without re-fetching
9. Clicking Connections tab again does NOT re-fetch (hx-trigger="click once")
</verification>

<success_criteria>
- Tab bar renders with Schema (active by default) and Connections tabs
- Connections tab lazy-loads SPARQL results via GET /admin/models/{model_id}/connections
- Connections grouped by predicate label with direction (outbound/inbound) sections
- Each connection clickable to open in browser workspace
- Empty state displayed when no connections exist
- No page reload or full navigation -- htmx partial swap only
</success_criteria>

<output>
After completion, create `.planning/quick/11-add-connections-tab-to-mental-model-deta/11-SUMMARY.md`
</output>
