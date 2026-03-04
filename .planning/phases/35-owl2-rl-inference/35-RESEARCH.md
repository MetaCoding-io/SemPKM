# Phase 35: OWL 2 RL Inference - Research

**Researched:** 2026-03-04
**Domain:** OWL 2 RL forward-chaining inference, RDF named graph management, htmx bottom panel UI
**Confidence:** HIGH

## Summary

Phase 35 adds manual OWL 2 RL inference to SemPKM so that declared OWL axioms (primarily `owl:inverseOf`) are materialized as triples. The basic-pkm ontology already declares `bpkm:participatesIn owl:inverseOf bpkm:hasParticipant` but no reasoner is configured -- users must manually create both directions. The `owlrl` Python library (v7.1.4, same RDFLib ecosystem as pyshacl) implements the full OWL 2 RL profile as forward-chaining closure expansion on rdflib graphs. This is the correct tool: it requires no triplestore reconfiguration, operates on graphs already available in the validation pipeline, and handles all entailment types the user wants configurable (inverseOf, subClassOf, subPropertyOf, TransitiveProperty, domain/range).

The user chose a manual trigger model (not automatic on every write). Inference runs when the user clicks "Refresh" in a new "Inference" bottom panel tab. Inferred triples are stored in `urn:sempkm:inferred` named graph, visually distinguished in the UI (badges in relations panel, dashed lines in graph view, right-column placement in object read view), and can be dismissed or promoted to permanent user triples. The inference scope is configurable per Mental Model in the admin panel, with concrete examples from the model's ontology.

**Primary recommendation:** Create a new `InferenceService` that loads ontology graphs, applies selective OWL 2 RL entailments via owlrl, diffs original vs. expanded graph, and stores results in `urn:sempkm:inferred`. Wire it to a new `/api/inference/run` endpoint triggered from the Inference bottom panel tab. Modify all SPARQL queries that read `urn:sempkm:current` to optionally also read from `urn:sempkm:inferred` (via FROM clause injection), and annotate inferred triples in UI rendering.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Subtle "inferred" badge on inferred triples in the relations panel -- small label or icon, not overwhelming
- Dashed lines for inferred edges in graph view (solid lines remain for user-created edges)
- Object read view: inferred properties in a right-hand column, user-created properties on the left
- Inferred relation links are fully clickable/navigable -- behave identically to manually-created links
- Manual trigger only for v2.4 -- user clicks a "Refresh" button in the Inference bottom panel tab
- No automatic inference on every write (auto option deferred to future configuration)
- Stale inferred triples (source deleted) get a visual indicator with pop-up explanation describing what happened
- Manual/user-created triples always take precedence over inferred triples (no duplication, no override)
- Each inference run creates an entry in the event log for auditability
- New "Inference" tab in the bottom panel (alongside SPARQL, Event Log, AI Copilot)
- Contains a "Refresh" button to trigger inference
- Shows a global list of all inferred triples (not just summary counts)
- Filterable by object type and date range
- Groupable by: time inferred (chronological), object type, or property type
- Users can dismiss/hide individual inferred triples from this panel
- Users can "pin"/promote individual inferred triples to permanent user-created triples from this panel
- Users can dismiss/hide specific inferred triples they don't want to see (per-triple opt-out)
- Users can promote ("pin") an inferred triple to a permanent user-created triple that persists even if the source is removed
- Inferred triples are otherwise read-only -- cannot be directly edited, only dismissed or promoted
- Configurable per Mental Model in admin panel (model management section)
- Mental Model author provides default entailment toggles in the manifest
- User can override defaults: check/uncheck which OWL RL entailment types to enable per model
- Available entailment types: `owl:inverseOf`, `rdfs:subClassOf`, `rdfs:subPropertyOf`, `owl:TransitiveProperty`, `rdfs:domain`/`rdfs:range`
- Admin UI shows concrete examples from the model's actual ontology (e.g., "hasParticipant <-> participatesIn" not just "owl:inverseOf")
- Mental Model uninstall cleans up inferred triples following existing uninstall pattern (same as other model data)

### Claude's Discretion
- Named graph strategy for `urn:sempkm:inferred` (full recompute vs incremental on each run)
- Exact inference panel layout and table/list design
- Toast or inline feedback during inference run progress
- How to handle conflicting inferred triples from multiple Mental Models
- Badge styling and stale-triple pop-up implementation details

### Deferred Ideas (OUT OF SCOPE)
- Automatic inference on every write (user-configurable auto mode) -- future enhancement after users understand manual workflow
- AI explainability for inferred triples ("why was this inferred?" -- trace the axiom chain) -- significant capability, own phase
- SHACL-AF rules (sh:TripleRule, sh:SPARQLRule) -- Phase 36
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| INF-01 | User adds a participant to a Project; the Person's detail page automatically shows the Project in their "participatesIn" list without manual inverse entry (OWL 2 RL inference materializes `owl:inverseOf` triples) | owlrl `DeductiveClosure(OWLRL_Semantics).expand(g)` materializes inverse triples from `owl:inverseOf` axioms already declared in `basic-pkm.jsonld`. Inferred triples stored in `urn:sempkm:inferred` and surfaced in object views and relations panel. |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| owlrl | 7.1.4 | OWL 2 RL + RDFS forward-chaining inference on rdflib graphs | Same RDFLib ecosystem as pyshacl; pure Python; handles all OWL 2 RL entailment types |
| rdflib | >=7.5.0 (already installed) | RDF graph manipulation, SPARQL, serialization | Already the core RDF library in SemPKM |
| pyshacl | >=0.31.0 (already installed) | SHACL validation (existing); can invoke owlrl via `inference='owlrl'` | Already in stack; not used for inference in this phase (manual trigger is separate from validation) |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| htmx | 1.9.x (already loaded) | Dynamic bottom panel tab, inference trigger, triple list rendering | All Inference panel UI interactions |
| Lucide | (already loaded) | Icons for inference badge, dismiss/promote buttons | UI elements |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| owlrl standalone | pyshacl `inference='owlrl'` parameter | pyshacl integration runs owlrl + validation in one pass, but the user wants inference decoupled from validation (manual trigger). Standalone owlrl gives explicit control over when inference runs and what triples are extracted. |
| Python-side owlrl | RDF4J SchemaCachingRDFSInferencer | RDF4J only supports RDFS (not OWL), requires repo recreation and triplestore reconfiguration. Explicitly out of scope per REQUIREMENTS.md. |
| Full OWL 2 RL closure | Selective entailment filtering | Full closure generates many triples (domain/range type assertions, etc.) that may be noisy. User wants configurable entailment types per model. Selective filtering is the right approach. |

**Installation:**
```bash
# Add to backend/pyproject.toml dependencies:
"owlrl>=7.0",
# Then rebuild Docker:
docker compose build backend
```

## Architecture Patterns

### Recommended Project Structure
```
backend/app/
├── inference/                  # NEW: inference module
│   ├── __init__.py
│   ├── service.py              # InferenceService: orchestrates inference runs
│   ├── router.py               # API endpoints: /api/inference/run, /api/inference/triples
│   ├── entailments.py          # Selective entailment filtering (per-type closure)
│   └── models.py               # Data models: InferenceRun, InferredTriple, DismissedTriple
├── services/
│   └── models.py               # MODIFIED: add ontology loader, entailment config storage
├── models/
│   └── manifest.py             # MODIFIED: add optional entailment_defaults to manifest
└── templates/browser/
    ├── workspace.html           # MODIFIED: add Inference tab to bottom panel
    ├── inference_panel.html     # NEW: inference panel with triple list, filters, actions
    ├── object_read.html         # MODIFIED: two-column layout for inferred properties
    └── properties.html          # MODIFIED: inferred badge on relation items
```

### Pattern 1: Separate Inference Service (Decoupled from Validation)

**What:** A new `InferenceService` that runs OWL 2 RL inference independently of the validation pipeline.

**When to use:** The user explicitly chose manual trigger, not automatic on every write. Inference is a separate concern from SHACL validation.

**Why not integrate into ValidationService:** The existing `ValidationService.validate()` runs after every `EventStore.commit()` via `AsyncValidationQueue`. Adding inference there would make it automatic (violating the locked decision). The `InferenceService` runs only on explicit user request.

**Example:**
```python
# backend/app/inference/service.py
from owlrl import DeductiveClosure, OWLRL_Semantics
from rdflib import Graph, URIRef

INFERRED_GRAPH_IRI = URIRef("urn:sempkm:inferred")

class InferenceService:
    def __init__(self, client: TriplestoreClient):
        self._client = client

    async def run_inference(self, entailment_config: dict) -> InferenceResult:
        """Run OWL 2 RL inference on current state + ontology graphs.

        1. Fetch current state graph from urn:sempkm:current
        2. Fetch ontology graphs from all installed models
        3. Merge data + ontology into working graph
        4. Run owlrl DeductiveClosure
        5. Diff: new_triples = expanded - original_data - ontology
        6. Filter by enabled entailment types
        7. Remove dismissed triples
        8. Clear and rewrite urn:sempkm:inferred
        9. Log inference run as event
        """
        ...
```

### Pattern 2: Full Recompute on Each Run (Not Incremental)

**What:** Each inference run drops `urn:sempkm:inferred` and recomputes all inferred triples from scratch.

**When to use:** For PKM-scale data (thousands of triples, not millions). Full recompute is simpler, avoids stale-triple accumulation bugs, and is fast enough (<500ms).

**Why not incremental:** Incremental inference requires tracking which source triples generated which inferred triples (provenance). When a source triple is deleted, you must find and remove only those inferred triples derived from it. This is complex and error-prone. Full recompute sidesteps all of this: the inferred graph is always consistent with the current state.

**Stale detection:** After recompute, compare old inferred set vs. new inferred set. Triples in old but not new are "stale" -- their source was deleted. These get a visual indicator (not an error, just an informational "the source relationship was removed" note).

### Pattern 3: Named Graph Strategy for Inferred Triples

**What:** Store all inferred triples in `urn:sempkm:inferred`, separate from `urn:sempkm:current` (user data).

**How it works:**
- User-created data lives in `urn:sempkm:current` (existing)
- Inferred triples live in `urn:sempkm:inferred` (new)
- SPARQL queries add `FROM <urn:sempkm:inferred>` alongside `FROM <urn:sempkm:current>` to see both
- The relations endpoint, object read endpoint, and graph view queries are updated to query both graphs
- A flag or CSS class distinguishes inferred results from user results in the UI

**Named graph contents:**
```turtle
# urn:sempkm:inferred contains:
# 1. The inferred triples themselves
<urn:sempkm:model:basic-pkm:person-1> <urn:sempkm:model:basic-pkm:participatesIn> <urn:sempkm:model:basic-pkm:project-1> .

# 2. Metadata about each triple (for dismiss/promote/staleness)
# Stored in a separate metadata graph or as reification
```

**Metadata approach:** Use a separate `urn:sempkm:inference:meta` named graph with RDF reification or a custom triple-identifier scheme to track per-triple state (dismissed, promoted, stale). This avoids polluting the inferred graph with metadata.

### Pattern 4: Selective Entailment Filtering

**What:** Rather than running full OWL 2 RL closure (which generates domain/range type assertions, symmetric property closure, etc.), filter the expanded triples to only include entailment types the user has enabled.

**How it works:**
```python
# After owlrl.DeductiveClosure(OWLRL_Semantics).expand(merged_graph):
new_triples = set(merged_graph) - set(data_graph) - set(ontology_graph)

# Filter by entailment type
enabled = {"owl:inverseOf", "rdfs:subClassOf"}  # from admin config
filtered = []
for s, p, o in new_triples:
    if _is_inverse_entailment(s, p, o, ontology_graph) and "owl:inverseOf" in enabled:
        filtered.append((s, p, o))
    elif _is_subclass_entailment(s, p, o, ontology_graph) and "rdfs:subClassOf" in enabled:
        filtered.append((s, p, o))
    # ... etc
```

**Classification heuristic:** To determine which entailment type produced a triple, check the ontology axioms:
- **inverseOf**: triple `?x ?q ?y` where ontology says `?q owl:inverseOf ?p` and data has `?y ?p ?x`
- **subClassOf**: triple `?x rdf:type ?C` where ontology says `?D rdfs:subClassOf ?C` and data has `?x rdf:type ?D`
- **subPropertyOf**: triple `?x ?P ?y` where ontology says `?p rdfs:subPropertyOf ?P` and data has `?x ?p ?y`
- **TransitiveProperty**: triple `?x ?p ?z` where ontology says `?p a owl:TransitiveProperty` and data has `?x ?p ?y` and `?y ?p ?z`
- **domain/range**: triple `?x rdf:type ?C` where ontology says `?p rdfs:domain ?C` (or `rdfs:range`) and data has `?x ?p ?y`

### Pattern 5: Dual-Graph SPARQL Query Modification

**What:** Modify existing SPARQL queries to include inferred triples by adding FROM clauses.

**Where queries need changes:**
1. **Relations panel** (`browser/router.py` `get_relations()`): Queries `GRAPH <urn:sempkm:current>` for outbound/inbound edges. Must also query `GRAPH <urn:sempkm:inferred>` and annotate results with source graph.
2. **Object read view** (`browser/router.py` `get_object_tab()`): Fetches property values from current graph. Must also fetch from inferred graph.
3. **Graph view** (`views/service.py` `execute_graph_query()`, `expand_neighbors()`): Uses `scope_to_current_graph()` to inject FROM clauses. Must add inferred graph.
4. **Labels service** (`services/labels.py`): Queries `FROM <urn:sempkm:current>`. Should also resolve labels from inferred graph.

**Implementation:** The `scope_to_current_graph()` function in `app/sparql/client.py` is the centralized injection point. Extend it to optionally also inject `FROM <urn:sempkm:inferred>`:
```python
def scope_to_current_graph(query: str, include_inferred: bool = True) -> str:
    # Existing: injects FROM <urn:sempkm:current>
    # New: also injects FROM <urn:sempkm:inferred> when include_inferred=True
```

### Anti-Patterns to Avoid
- **Storing inferred triples in `urn:sempkm:current`:** This mixes user data with machine-generated data. Users cannot distinguish what they created vs. what the system inferred. Model uninstall cannot cleanly remove inferred triples. Full recompute would require complex diffing against current state.
- **Running inference inside EventStore.commit():** This violates the user's locked decision for manual trigger. It also adds latency to every write operation.
- **Using pyshacl `inference='owlrl'` for the manual trigger:** While pyshacl can invoke owlrl, it couples inference to validation. The user wants inference to be a separate action with its own UI and controls.
- **Incremental inference without provenance tracking:** If you try to incrementally add/remove inferred triples without tracking which source triple produced which inferred triple, you will get stale triples accumulating.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| OWL 2 RL reasoning | Custom SPARQL CONSTRUCT rules per axiom type | `owlrl.DeductiveClosure(OWLRL_Semantics).expand(g)` | owlrl implements the complete OWL 2 RL rule table (Tables 4-9 of the W3C spec). Hand-rolling inverseOf is easy but subClassOf transitivity, domain/range, and symmetric properties have subtle edge cases. |
| Graph differencing | Manual triple-by-triple comparison | Python set operations on rdflib triples: `set(expanded) - set(original)` | rdflib triples are hashable tuples; set difference is O(n) and correct. |
| SPARQL serialization | Custom triple-to-SPARQL converters | Existing `_rdf_term_to_sparql()` in `events/store.py` and `models/registry.py` | Already battle-tested in the codebase for INSERT DATA, DELETE WHERE. |

**Key insight:** owlrl is a well-maintained RDFLib project (same org as pyshacl and rdflib). It is the standard Python library for OWL 2 RL inference. The latest version (7.1.4, released July 2025) is compatible with rdflib 7.x already in the project.

## Common Pitfalls

### Pitfall 1: owlrl Generates Thousands of rdf:type Triples from Domain/Range Axioms
**What goes wrong:** Running full OWL 2 RL closure on data with `rdfs:domain`/`rdfs:range` declarations generates `rdf:type` assertions for every entity that uses a typed property. With 5 properties each having domain+range, and 1000 data triples, this can add 2000+ type triples.
**Why it happens:** OWL 2 RL domain/range rules say: if `?p rdfs:domain ?C` and `?x ?p ?y`, then `?x rdf:type ?C`. This is logically correct but noisy for a PKM UI.
**How to avoid:** The selective entailment filtering (Pattern 4) lets users disable domain/range inference. Default should have it OFF unless the user explicitly enables it.
**Warning signs:** Inference panel shows hundreds of `rdf:type` triples that are not useful to the user.

### Pitfall 2: Blank Nodes in owlrl Expansion
**What goes wrong:** owlrl may create blank nodes during closure expansion (e.g., for existential restrictions). Blank nodes cannot be stored in RDF4J via SPARQL INSERT DATA (they get new identifiers on each insert).
**Why it happens:** OWL 2 RL includes some rules that create anonymous individuals.
**How to avoid:** Filter out any triples containing blank nodes before storing to `urn:sempkm:inferred`. At PKM scale with simple ontologies (no existential restrictions), this should not lose meaningful inferred triples.
**Warning signs:** SPARQL INSERT DATA fails with blank node serialization errors.

### Pitfall 3: Duplicate Triples When User-Created and Inferred Overlap
**What goes wrong:** If the user manually creates `PersonB bpkm:participatesIn ProjectA` AND inference also produces the same triple (from `ProjectA bpkm:hasParticipant PersonB`), the UI shows duplicates.
**Why it happens:** Both `urn:sempkm:current` and `urn:sempkm:inferred` contain the same triple.
**How to avoid:** Before writing to `urn:sempkm:inferred`, filter out any triple that already exists in `urn:sempkm:current`. The user's locked decision says "manual/user-created triples always take precedence over inferred triples (no duplication, no override)."
**Warning signs:** Relations panel shows the same relationship twice.

### Pitfall 4: Large Ontology Graphs Slow Down owlrl
**What goes wrong:** Loading the full SKOS, FOAF, Dublin Core vocabularies alongside the model ontology into owlrl's working graph causes it to compute entailments across all vocabulary axioms, not just the model's.
**Why it happens:** owlrl processes ALL axioms in the merged graph, including standard vocabulary axioms.
**How to avoid:** Only load model-specific ontology graphs (`urn:sempkm:model:{id}:ontology`), not external vocabularies. The model ontology already imports what it needs.
**Warning signs:** Inference takes >5 seconds instead of <500ms.

### Pitfall 5: Named Graph Confusion in SPARQL Queries
**What goes wrong:** Existing SPARQL queries use `GRAPH <urn:sempkm:current>` clauses. Adding `FROM <urn:sempkm:inferred>` changes query semantics: FROM clauses define the default graph, while GRAPH clauses query named graphs. Mixing them produces empty results.
**Why it happens:** SPARQL `FROM` merges named graphs into the default graph, but `GRAPH <X>` queries the named graph directly. They don't interact as expected.
**How to avoid:** For queries using `GRAPH <urn:sempkm:current>`, use UNION to also query `GRAPH <urn:sempkm:inferred>`:
```sparql
{
  GRAPH <urn:sempkm:current> { ?s ?p ?o }
} UNION {
  GRAPH <urn:sempkm:inferred> { ?s ?p ?o }
}
```
For queries using `FROM <urn:sempkm:current>`, add `FROM <urn:sempkm:inferred>`:
```sparql
SELECT ?s ?p ?o
FROM <urn:sempkm:current>
FROM <urn:sempkm:inferred>
WHERE { ?s ?p ?o }
```
**Warning signs:** Inferred triples not appearing in relations panel or graph view despite being stored.

### Pitfall 6: Stale-Triple Detection After Source Deletion
**What goes wrong:** User deletes `ProjectA bpkm:hasParticipant PersonB`. On next inference run, `PersonB bpkm:participatesIn ProjectA` is no longer inferred. But between runs (before the user clicks Refresh), the stale triple is still in `urn:sempkm:inferred`.
**Why it happens:** Manual inference means there is a gap between write and re-inference.
**How to avoid:** The user explicitly chose this behavior (manual trigger). The stale-triple visual indicator (locked decision) informs the user. A "last run" timestamp in the Inference panel shows when inference was last computed. After recompute, stale triples simply disappear.
**Warning signs:** User confusion about why an inferred triple still appears after deleting the source.

## Code Examples

### owlrl Inference on rdflib Graph
```python
# Source: https://pypi.org/project/owlrl/ + codebase analysis
import owlrl
from rdflib import Graph

# 1. Load data and ontology
data = Graph()
data.parse(data=turtle_bytes, format="turtle")  # from CONSTRUCT on urn:sempkm:current

ontology = Graph()
ontology.parse(data=ont_bytes, format="turtle")  # from CONSTRUCT on model ontology graphs

# 2. Merge into working graph (keep original separate for diffing)
original_triples = set(data)
working = data + ontology

# 3. Run OWL 2 RL closure
owlrl.DeductiveClosure(owlrl.OWLRL_Semantics).expand(working)

# 4. Extract new inferred triples
ontology_triples = set(ontology)
all_after = set(working)
new_triples = all_after - original_triples - ontology_triples

# new_triples contains all inferred triples (inverses, type assertions, etc.)
```

### Selective Entailment Filtering
```python
# Source: codebase analysis of basic-pkm.jsonld ontology structure
from rdflib import OWL, RDF, RDFS

def classify_entailment(s, p, o, ontology: Graph) -> str | None:
    """Classify an inferred triple by which entailment type produced it."""
    # Check owl:inverseOf
    if (p, OWL.inverseOf, None) in ontology or (None, OWL.inverseOf, p) in ontology:
        return "owl:inverseOf"
    # Check rdf:type from rdfs:subClassOf
    if p == RDF.type:
        for parent_class in ontology.objects(o, RDFS.subClassOf):
            return "rdfs:subClassOf"
        # Check rdf:type from rdfs:domain/rdfs:range
        for prop in ontology.subjects(RDFS.domain, o):
            return "rdfs:domain/rdfs:range"
        for prop in ontology.subjects(RDFS.range, o):
            return "rdfs:domain/rdfs:range"
    # Check rdfs:subPropertyOf
    for parent_prop in ontology.objects(p, RDFS.subPropertyOf):
        return "rdfs:subPropertyOf"
    # Check owl:TransitiveProperty
    if (p, RDF.type, OWL.TransitiveProperty) in ontology:
        return "owl:TransitiveProperty"
    return None
```

### Ontology Loader (Parallel to Existing Shapes Loader)
```python
# Source: pattern from model_shapes_loader() in services/models.py
async def model_ontology_loader(client: TriplestoreClient) -> Graph:
    """Load ontology graphs from all installed models."""
    sparql = f"""SELECT ?modelId WHERE {{
      GRAPH <urn:sempkm:models> {{
        ?model a <urn:sempkm:MentalModel> ;
               <urn:sempkm:modelId> ?modelId .
      }}
    }}"""
    result = await client.query(sparql)
    bindings = result.get("results", {}).get("bindings", [])

    if not bindings:
        return Graph()

    from_clauses = []
    for b in bindings:
        model_id = b["modelId"]["value"]
        from_clauses.append(f"FROM <urn:sempkm:model:{model_id}:ontology>")

    construct_sparql = f"CONSTRUCT {{ ?s ?p ?o }} {chr(10).join(from_clauses)} WHERE {{ ?s ?p ?o }}"
    turtle_bytes = await client.construct(construct_sparql)
    ontology = Graph()
    if turtle_bytes.strip():
        ontology.parse(data=turtle_bytes, format="turtle")
    return ontology
```

### Duplicate Filtering (User Triples Take Precedence)
```python
# Source: codebase analysis of urn:sempkm:current graph pattern
async def filter_against_current(
    client: TriplestoreClient,
    inferred_triples: set[tuple],
) -> set[tuple]:
    """Remove inferred triples that already exist in urn:sempkm:current."""
    current_bytes = await client.construct(
        "CONSTRUCT { ?s ?p ?o } FROM <urn:sempkm:current> WHERE { ?s ?p ?o }"
    )
    current = Graph()
    if current_bytes.strip():
        current.parse(data=current_bytes, format="turtle")
    current_set = set(current)
    return inferred_triples - current_set
```

### Bottom Panel Tab Addition (Following Existing Pattern)
```html
<!-- Source: workspace.html bottom panel pattern -->
<!-- Add to panel-tab-bar in workspace.html -->
<button class="panel-tab" data-panel="inference">INFERENCE</button>

<!-- Add to panel-content in workspace.html -->
<div class="panel-pane" id="panel-inference">
  <div class="inference-panel-header">
    <button class="btn btn-sm inference-refresh-btn"
            hx-post="/api/inference/run"
            hx-target="#inference-results"
            hx-swap="innerHTML"
            hx-indicator="#inference-spinner">
      <i data-lucide="refresh-cw"></i> Refresh
    </button>
    <span class="inference-spinner htmx-indicator" id="inference-spinner">
      Running...
    </span>
    <span class="inference-last-run" id="inference-last-run"></span>
  </div>
  <div class="inference-filters">
    <!-- Object type filter, date range, grouping controls -->
  </div>
  <div class="inference-results" id="inference-results">
    <!-- htmx-loaded triple list -->
  </div>
</div>
```

### Relations Panel with Inferred Badge
```python
# Source: browser/router.py get_relations() pattern
# Modified query to include inferred graph with source annotation
outbound_sparql = f"""
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
SELECT ?predicate ?object ?source WHERE {{
  {{
    GRAPH <urn:sempkm:current> {{
      <{iri}> ?predicate ?object .
      FILTER(isIRI(?object))
      FILTER(?predicate != rdf:type)
    }}
    BIND("user" AS ?source)
  }} UNION {{
    GRAPH <urn:sempkm:inferred> {{
      <{iri}> ?predicate ?object .
      FILTER(isIRI(?object))
      FILTER(?predicate != rdf:type)
    }}
    BIND("inferred" AS ?source)
  }}
}}
"""
```

### Manifest Entailment Defaults
```yaml
# Source: manifest.yaml pattern from models/basic-pkm/manifest.yaml
modelId: basic-pkm
version: "1.1.0"
# ... existing fields ...
entailment_defaults:
  owl_inverseOf: true
  rdfs_subClassOf: false
  rdfs_subPropertyOf: false
  owl_TransitiveProperty: false
  rdfs_domain_range: false
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| No inference -- users manually create bidirectional links | owlrl materializes OWL 2 RL entailments from declared axioms | Phase 35 | Automatic bidirectional links; richer graph visualization |
| Single named graph (`urn:sempkm:current`) for all data | Dual named graphs: `current` (user) + `inferred` (machine) | Phase 35 | Clean separation of user vs. derived data; easy recomputation |
| Validation pipeline only (pyshacl) | Validation + separate inference service (pyshacl + owlrl) | Phase 35 | Two distinct capabilities: correctness checking vs. knowledge derivation |

**Deprecated/outdated:**
- RDF4J server-side inference via SchemaCachingRDFSInferencer: Explicitly out of scope per REQUIREMENTS.md ("RDF4J server-side inference -- Python-side owlrl is sufficient; triplestore reconfiguration deferred")

## Open Questions

1. **Per-triple metadata storage for dismiss/promote/stale tracking**
   - What we know: Need to track state per inferred triple (active, dismissed, promoted). Promoted triples should be copied to `urn:sempkm:current` via EventStore.
   - What's unclear: Best storage mechanism -- RDF reification in a metadata graph, a SQLite table mapping (s,p,o) hashes to state, or inline RDF-star annotations?
   - Recommendation: Use a SQLite table (`inference_triple_state`) with columns `(triple_hash TEXT PK, status TEXT, dismissed_at TEXT, promoted_at TEXT)`. This avoids RDF complexity and is fast for lookup. The `triple_hash` is a deterministic hash of `(subject, predicate, object)`.

2. **Entailment config storage location**
   - What we know: Per-model entailment toggles need to persist across sessions. The manifest provides defaults; users override in admin UI.
   - What's unclear: Store in SQLite (settings table), triplestore (model registry graph), or both?
   - Recommendation: Use the existing `SettingsService` pattern -- store in SQLite settings table with keys like `inference.basic-pkm.owl_inverseOf=true`. This is consistent with other per-model settings.

3. **Handling multiple Mental Models with conflicting inference**
   - What we know: Multiple models could have overlapping ontology axioms. owlrl processes the merged ontology.
   - What's unclear: If Model A declares `?p owl:inverseOf ?q` and Model B redeclares the same, does this cause issues?
   - Recommendation: Not a real problem -- OWL axioms are idempotent. Duplicate declarations don't change the closure. If models have contradictory axioms (unlikely in practice), owlrl will compute the union, which may produce unexpected triples. The selective filtering provides a safety valve.

4. **Performance of full recompute at scale**
   - What we know: owlrl on a 5,000-triple graph with simple ontology takes <500ms (per prior research). Full graph fetch via CONSTRUCT may be slower on large graphs.
   - What's unclear: How the CONSTRUCT fetch of `urn:sempkm:current` scales beyond 10,000 triples.
   - Recommendation: For v2.4, full recompute is sufficient. If users report slowness, add graph-size check and warn before running on large graphs.

## Sources

### Primary (HIGH confidence)
- [owlrl on PyPI](https://pypi.org/project/owlrl/) - Version 7.1.4, released July 2025, requires rdflib 7.1.3
- [owlrl on GitHub](https://github.com/RDFLib/OWL-RL) - RDFLib project, OWL 2 RL + RDFS reasoning
- [W3C OWL 2 Profiles](https://www.w3.org/TR/owl2-profiles/) - OWL 2 RL profile specification (Section 4.3)
- `.planning/research/shacl-owl-inference.md` - Prior in-project research (quick task 19)
- `backend/app/services/validation.py` - Existing ValidationService pattern
- `backend/app/services/models.py` - Existing model_shapes_loader() pattern
- `models/basic-pkm/ontology/basic-pkm.jsonld` - Existing owl:inverseOf declaration

### Secondary (MEDIUM confidence)
- [pyshacl Advanced Features](https://github.com/RDFLib/pySHACL#advanced-features) - inference='owlrl' parameter docs
- [RDF4J RDFS Reasoning](https://rdf4j.org/documentation/programming/rdfs-reasoning/) - Why RDF4J inference is out of scope

### Tertiary (LOW confidence)
- Performance estimates (500ms for 5,000 triples) are from prior research document, not benchmarked on this project's actual data

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - owlrl is the canonical Python library for OWL 2 RL inference, same ecosystem as rdflib/pyshacl
- Architecture: HIGH - Patterns derived from deep analysis of existing codebase (EventStore, ValidationService, model_shapes_loader, workspace.html)
- Pitfalls: HIGH - Pitfalls 1-5 identified from RDF/SPARQL domain expertise and codebase-specific named graph patterns; Pitfall 6 from user's manual trigger decision

**Research date:** 2026-03-04
**Valid until:** 2026-04-04 (stable domain, library versions unlikely to change)
