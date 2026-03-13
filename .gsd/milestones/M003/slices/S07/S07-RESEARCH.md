# S07: Ontology Viewer & Gist Foundation — Research

**Date:** 2026-03-12

## Summary

S07 delivers the ontology viewer (TBox Explorer, ABox Browser, RBox Legend) and loads gist 14.0.0 as the foundation upper ontology. The codebase already has strong patterns to build on: multi-graph SPARQL with `FROM` clauses (inference service), model ontology diagram with Cytoscape.js (admin), collapsible htmx trees (explorer modes), and dockview panel types for workspace views. The primary technical risk is cross-graph class hierarchy SPARQL — querying `rdfs:subClassOf` chains that span `urn:sempkm:ontology:gist` plus N model ontology graphs. This is solvable with `FROM` clause aggregation (same pattern as `_load_ontology_graphs()` in inference service). Gist 14.0.0 is a single 138KB Turtle file (~3400 lines, ~96 classes, ~60 properties, 45 subClassOf triples) — small enough to load via the existing `_build_insert_data_sparql` pipeline using rdflib.

The recommended approach: load gist as a bundled Turtle file shipped with the backend (not downloaded at runtime), parse with rdflib, and INSERT DATA into `urn:sempkm:ontology:gist` during startup. The ontology viewer renders as a new dockview panel type (`special-panel` with `specialType: 'ontology'`), using htmx partials for TBox tree, ABox instance lists, and RBox property tables. Mental model → gist alignment triples are added to model ontology files as `rdfs:subClassOf` statements. No JS graph library needed for the tree views — collapsible HTML trees with htmx lazy-loading match the explorer pattern.

## Recommendation

Build the ontology viewer as three htmx-rendered tabs (TBox/ABox/RBox) inside a workspace panel, not as a sidebar section. Use the existing `special-panel` dockview component type with a `/browser/ontology` route. Load gist once at startup into its own named graph. Query class hierarchy across all ontology graphs using `FROM` clause aggregation. Add alignment triples to existing model ontology JSON-LD files (basic-pkm, ppv).

### Why this approach:
1. **Startup loading** — avoids runtime HTTP fetches to GitHub; gist version is pinned and bundled
2. **special-panel in dockview** — reuses existing panel infrastructure; ontology viewer opens like canvas/VFS browser
3. **htmx tree for TBox** — consistent with explorer modes; lazy-load children avoids rendering all ~96 gist classes at once
4. **FROM clause aggregation** — proven pattern in inference service; spans gist + all model ontology graphs in one query
5. **Alignment in model ontology files** — keeps model packages self-describing; no runtime injection

## Don't Hand-Roll

| Problem | Existing Solution | Why Use It |
|---------|------------------|------------|
| Turtle parsing for gist file | rdflib (already a dependency) | Used by inference service, model loader, shapes service — battle-tested in this codebase |
| Named graph INSERT DATA | `_build_insert_data_sparql()` in `services/models.py` | Triple-by-triple serialization handles all rdflib term types correctly |
| Multi-graph SPARQL queries | `FROM` clause aggregation in inference service | `_load_ontology_graphs()` already queries all model ontology graphs — just add gist graph |
| Collapsible tree rendering | Explorer mode htmx patterns (`hierarchy_tree.html`, `hierarchy_children.html`) | Same UX pattern: parent nodes with lazy `hx-trigger="click once"` children |
| Workspace panel hosting | `special-panel` component in `workspace-layout.js` | Already handles canvas, VFS browser — just add `ontology` specialType |
| Label resolution for IRIs | `LabelService.resolve_batch()` | Handles `skos:prefLabel`, `rdfs:label`, `dcterms:title` — gist uses `skos:prefLabel` |
| Type icon display | `IconService.get_type_icon()` | Used in all tree views for consistent type presentation |

## Existing Code and Patterns

### Graph Loading & Querying
- `backend/app/inference/service.py:410-440` — `_load_ontology_graphs()` aggregates `FROM <urn:sempkm:model:{id}:ontology>` clauses from all installed models. **Reuse this pattern** for TBox queries adding `FROM <urn:sempkm:ontology:gist>`.
- `backend/app/services/models.py:_build_insert_data_sparql()` — Serializes rdflib Graph into SPARQL INSERT DATA for a named graph. **Reuse** for loading gist Turtle into `urn:sempkm:ontology:gist`.
- `backend/app/models/registry.py:write_graph_to_named_graph()` — Higher-level wrapper that calls the same pattern. Can be used directly.
- `backend/app/triplestore/client.py` — `query()` returns JSON, `construct()` returns Turtle bytes, `update()` executes SPARQL UPDATE. All async.

### Explorer Tree Patterns
- `backend/app/browser/workspace.py:EXPLORER_MODES` — Dict mapping mode names to handler functions. Reference for how mode handlers receive `request`, `label_service`, `icon_svc`.
- `backend/app/browser/workspace.py:_handle_hierarchy()` — Queries root objects, resolves labels, renders `hierarchy_tree.html`. The TBox Explorer follows the same pattern: query root classes, lazy-load subclasses.
- `backend/app/templates/browser/hierarchy_tree.html` + `hierarchy_children.html` — Collapsible tree nodes with `hx-get` for lazy child expansion. **Direct template pattern** for TBox tree.

### Workspace Panel System
- `frontend/static/js/workspace-layout.js:206-212` — `special-panel` component type: creates a `div.group-editor-area`, fetches `/browser/{specialType}` via htmx. Adding `ontology` as a specialType just requires a `/browser/ontology` route.
- `frontend/static/js/workspace.js:openTab()` and `openViewTab()` — Reference for how workspace tabs open; ontology viewer would use a similar `openOntologyTab()` or `openSpecialTab('ontology')`.

### Admin Ontology Diagram (reference for property/class queries)
- `backend/app/admin/router.py:149-228` — `admin_model_ontology_diagram()` queries model detail for types, properties, builds Cytoscape.js graph. The SPARQL queries in `ModelService._query_types()` and `_query_properties()` are a direct reference for RBox property queries.
- `backend/app/services/models.py:_query_types()` — Queries `owl:Class` with `rdfs:label` from a single ontology graph. For TBox, extend to query across gist + all model graphs.
- `backend/app/services/models.py:_query_properties()` — Queries `owl:ObjectProperty` and `owl:DatatypeProperty` with domain/range. Directly reusable for RBox Legend.

### Model Architecture
- `backend/app/models/registry.py:ModelGraphs` — Named graph convention: `urn:sempkm:model:{id}:ontology`, `urn:sempkm:model:{id}:shapes`, etc.
- `models/basic-pkm/ontology/basic-pkm.jsonld` — OWL class definitions. Alignment triples (`rdfs:subClassOf gist:...`) will be added here.
- `models/ppv/ontology/ppv.jsonld` — PPV model classes (PillarGroup, Pillar, ValueGoal, GoalOutcome, etc.). Needs alignment triples.

### Startup Lifecycle
- `backend/app/main.py:167` — `ensure_starter_model()` called during lifespan. Gist loading should follow a similar pattern: check if gist graph exists, load if missing, skip if current version.

## Constraints

- **Gist is Turtle format** — `gistCore.ttl` (138KB, 3438 lines). Must parse with rdflib and serialize to SPARQL INSERT DATA since RDF4J doesn't accept direct Turtle upload via the SPARQL endpoint (needs `/statements` endpoint with Content-Type).
- **RDF4J cross-graph query** — `FROM` clauses create a merge of named graphs as the default dataset. This works for `SELECT` and `CONSTRUCT`. Cannot use `GRAPH` patterns inside `FROM`-scoped queries (the FROM defines the default graph, GRAPH patterns query named graphs). Use `FROM` aggregation for TBox.
- **No OWL reasoning for `owl:equivalentClass`** — Gist uses `owl:equivalentClass` with complex intersection bodies (e.g., `gist:Project = gist:Task ∩ hasSubtask`). RDF4J RDFS inference does NOT fire these. Only explicit `rdfs:subClassOf` triples will form the hierarchy. This is acceptable — alignment uses `rdfs:subClassOf` per decision D024/D026.
- **Gist uses `skos:prefLabel`** — LabelService already checks `skos:prefLabel` in its resolution chain. Gist class labels will resolve correctly.
- **CC BY 4.0 license** — Must include attribution to Semantic Arts. Do not mint new terms in `gist:` namespace.
- **The gist file must be bundled** — Cannot rely on internet access at startup. Ship `gistCore.ttl` in the backend directory (e.g., `backend/ontologies/gist/gistCore14.0.0.ttl`).
- **INSERT DATA size** — 3438 lines → ~137KB of Turtle → significant INSERT DATA query. May need to batch into chunks (e.g., 500 triples per INSERT) to avoid RDF4J request size limits or timeout.
- **Named graph convention** — Decision D026 sets `urn:sempkm:ontology:gist` as the graph IRI. This is separate from model graphs (`urn:sempkm:model:{id}:ontology`).
- **User-types graph** — Decision D027 sets `urn:sempkm:user-types` for S08. S07 doesn't write to it but the TBox query should include it for forward compatibility.

## Common Pitfalls

- **gist blank nodes in OWL restrictions** — gistCore.ttl uses `_:genid` blank nodes extensively for OWL class restrictions (`owl:intersectionOf`, `owl:someValuesFrom`). When loading via rdflib → INSERT DATA, blank node serialization must use `_:bN` syntax. The existing `_rdf_term_to_sparql(BNode)` handler in `services/models.py` does this correctly. However, if blank node IDs collide with existing triplestore data, RDF4J may merge them. Use the `GRAPH` clause to scope writes — blank nodes are graph-local in RDF4J.
- **INSERT DATA size limit** — ~4000 triples in a single INSERT DATA may hit RDF4J's default 2MB request body limit. Batch into groups of 500 triples per INSERT. The inference service's `_load_ontology_graphs()` uses CONSTRUCT (read), not INSERT (write), so it doesn't face this. Use transaction-scoped updates for atomicity.
- **Class hierarchy depth** — Gist has a shallow hierarchy (most classes are 1-2 levels deep from `owl:Thing`). Model classes add 1 more level. Total depth is typically 3-4. Lazy-load is still preferred for UX consistency but don't expect deep trees.
- **`owl:Thing` as root** — Many gist classes are direct subclasses of `owl:Thing` (implicit — no explicit `rdfs:subClassOf owl:Thing` triple). The TBox root query should treat classes with no explicit superclass as root-level, not try to find `owl:Thing` as a parent. Show `owl:Thing` as an implicit virtual root if needed.
- **Gist data instances** — `gistCore.ttl` includes some ABox instances (`gistd:_Aspect_altitude`, etc.) alongside TBox classes. The TBox query must filter to `owl:Class` types only. The ABox query should exclude gist's built-in instances (or show them clearly as gist-provided).
- **Multiple `rdf:type` per class** — Some gist classes are both `owl:Class` and have other types (equivalent class definitions use intersection/restriction patterns). Filter on `?class a owl:Class` to avoid picking up restriction blank nodes.
- **ABox instance counts must include inferred types** — If RDFS inference is active and `bpkm:Project rdfs:subClassOf gist:Task`, then `gist:Task` instances include `bpkm:Project` instances. The ABox query should use `FROM <urn:sempkm:current> FROM <urn:sempkm:inferred>` to include inferred type memberships.

## Open Risks

- **INSERT DATA batching** — If gist's ~4000 triples cause timeout on a single INSERT DATA, need to split into batched transactions. Risk: increased startup time. Mitigation: batch + transaction, or use RDF4J's REST API for direct Turtle upload to a named graph (bypassing SPARQL entirely).
- **RDF4J direct graph upload** — Alternative to INSERT DATA: `PUT /repositories/{id}/rdf-graphs/service?graph=<urn:sempkm:ontology:gist>` with `Content-Type: text/turtle` body. This is RDF4J's native graph management API and handles large uploads efficiently. Would need a new method on `TriplestoreClient`. Risk: small API surface change. Benefit: much simpler than INSERT DATA batching.
- **Alignment quality** — Mapping basic-pkm/ppv classes to gist requires domain judgment. Wrong alignments make the TBox hierarchy misleading. Risk: medium. Mitigation: keep alignment conservative (only clear mappings: Note→FormattedContent, Project→Task, Person→Person, Concept→KnowledgeConcept).
- **ABox Browser performance** — Instance counts per class require one SPARQL query per class (or a batch VALUES query). With ~100 gist classes + ~10 model classes, this could be 110+ counts. Risk: slow initial render. Mitigation: batch all type IRIs in a single `VALUES` query (same pattern as `get_type_analytics()` in `ModelService`).
- **TBox rendering for power users** — Gist has ~96 classes, many without instances. Showing all of them may overwhelm users. Risk: UX clutter. Mitigation: show gist classes with a faded/muted style, or show only those with subclasses or instances. Per D024, gist classes should be fully visible — but could be collapsed by default.
- **Gist version detection** — Need to detect if gist is already loaded and at the right version to avoid re-loading on every restart. Risk: version check query adds startup latency. Mitigation: ASK query for the ontology IRI (`<https://w3id.org/semanticarts/ontology/gistCore> a owl:Ontology`) is cheap.

## Skills Discovered

| Technology | Skill | Status |
|------------|-------|--------|
| RDF/SPARQL/OWL | `letta-ai/skills@sparql-university` | Available (36 installs) — low relevance, academic |
| OWL Ontology Modeling | `sfc-gh-tjia/coco_skill_ontology@ontology-semantic-modeler` | Available (10 installs) — low relevance |
| Cytoscape.js | none found | N/A — already used in admin ontology diagram |
| htmx | none found | N/A — already the project's core frontend pattern |

No skills are worth installing — the project already has all the needed patterns in-codebase.

## Sources

- Gist 14.0.0 source: `gistCore.ttl` (3438 lines, 138KB) from [github.com/semanticarts/gist v14.0.0](https://github.com/semanticarts/gist/tree/v14.0.0)
- Gist ontology research: `.planning/quick/2-research-how-the-gist-ontology-can-be-us/gist-ontology-research.md` (detailed class alignment map, property alignment, integration strategy)
- Ontology viewer research: `.planning/ontology-viewer-research.md` (tool landscape, TBox/ABox/RBox strategy, build-vs-buy analysis)
- Decisions register: `.gsd/DECISIONS.md` (D024 gist fully visible, D025 pin 14.0.0, D026 graph IRI, D027 user-types graph)
- RDF4J Graph Management REST API: [rdf4j.org/documentation/reference/rest-api/#graph-store-operations](https://rdf4j.org/documentation/reference/rest-api/) — direct PUT of Turtle to named graph
