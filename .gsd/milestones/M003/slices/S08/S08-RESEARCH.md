# S08: In-App Class Creation — Research

**Date:** 2026-03-12

## Summary

S08 delivers in-app class creation (TYPE-01, TYPE-02): a user creates a new RDF class via a form (name, icon, parent class, basic properties with datatypes), and the system generates OWL class triples plus a SHACL NodeShape that integrates with the existing form generation pipeline. The created class appears in the TBox ontology viewer, type picker, and can be used for object creation with auto-generated SHACL forms.

The critical integration surface is the ShapesService: it currently queries only `urn:sempkm:model:{id}:shapes` named graphs via `_fetch_shapes_graph()`. User-created types and their SHACL shapes must live in `urn:sempkm:user-types` (per D027), so ShapesService must be extended to also query this graph. The OntologyService already includes `urn:sempkm:user-types` in its `get_ontology_graph_iris()` FROM clauses, so TBox visibility requires no changes — classes written to that graph will appear automatically.

The main risk is correctness of the generated SHACL NodeShape: it must produce a shape that `ShapesService._extract_node_shape()` can parse into a valid `NodeShapeForm` with working property shapes. This is testable: generate the shape, load it into an rdflib Graph, and verify ShapesService extracts a valid form. The form template (`forms/object_form.html`) is already fully generic — it renders any `NodeShapeForm` regardless of origin.

## Recommendation

**Approach: Single endpoint + inline SPARQL INSERT DATA to `urn:sempkm:user-types`**

1. **Class creation form** — new template in `templates/browser/ontology/` with fields: class name (text), icon (searchable icon picker with common Lucide names), parent class (reference picker searching TBox classes), and a dynamic property list (each property: name, predicate IRI, datatype selector).

2. **Backend endpoint** — `POST /browser/ontology/create-class` on the ontology router. Validates input, generates OWL class triples + SHACL NodeShape triples, and writes them to `urn:sempkm:user-types` via batched INSERT DATA (same pattern as gist loading in `OntologyService`).

3. **ShapesService extension** — add `urn:sempkm:user-types` as an additional FROM clause in `_fetch_shapes_graph()` so user-created shapes are discovered alongside model shapes.

4. **IconService extension** — user-created type icons must be discoverable. Since IconService reads from manifest.yaml files (filesystem), user-created icons need a different path: store icon metadata as triples in `urn:sempkm:user-types` and add a query-based fallback in IconService (or store icon triples alongside the class and resolve at render time).

5. **IRI minting for user classes** — mint class IRIs under the `urn:sempkm:user-types:` namespace (e.g., `urn:sempkm:user-types:MyCustomClass`). Shape IRIs follow the same pattern with a `Shape` suffix.

## Don't Hand-Roll

| Problem | Existing Solution | Why Use It |
|---------|------------------|------------|
| OWL class triple pattern | `models/basic-pkm/ontology/basic-pkm.jsonld` | Reference structure for owl:Class + rdfs:label + rdfs:subClassOf |
| SHACL NodeShape pattern | `models/basic-pkm/shapes/basic-pkm.jsonld` | Reference for sh:NodeShape, sh:targetClass, sh:property with all attributes ShapesService expects |
| Batch SPARQL INSERT DATA | `OntologyService._build_insert_data_sparql()` | Proven pattern for writing batched triples to named graphs within transactions |
| Form generation from SHACL | `ShapesService + forms/object_form.html + _field.html` | Complete pipeline: shape → dataclass → Jinja2 form. Just produce a valid shape. |
| Label resolution in TBox | `OntologyService.get_root_classes()` COALESCE pattern | User classes with `rdfs:label` will be picked up automatically by TBox queries |
| Icon rendering | `IconService.get_type_icon()` | Needs extension for user types, but the interface is established |

## Existing Code and Patterns

- `backend/app/ontology/service.py` — `OntologyService` already includes `USER_TYPES_GRAPH` in `get_ontology_graph_iris()`. TBox queries via FROM clause aggregation will automatically include user-created classes. The `_build_insert_data_sparql()` and `_rdf_term_to_sparql()` helpers can be reused for writing class/shape triples.

- `backend/app/ontology/router.py` — Ontology router with TBox/ABox/RBox endpoints. The create-class endpoint belongs here alongside existing ontology management.

- `backend/app/services/shapes.py` — `ShapesService._fetch_shapes_graph()` queries only `urn:sempkm:model:{id}:shapes`. Must add `FROM <urn:sempkm:user-types>` to include user shapes. The `_extract_node_shape()` method parses any valid `sh:NodeShape` — no changes needed there. `get_types()` calls `get_node_shapes()` which calls `_fetch_shapes_graph()` — so the type picker will automatically show user types once the FROM clause is added.

- `backend/app/services/icons.py` — `IconService._build_cache()` reads from filesystem manifest.yaml files only. User-created type icons need a different storage mechanism. Two options: (a) add a SPARQL-based icon lookup fallback, or (b) store a separate JSON/YAML file for user type icons. Option (a) is more consistent with the RDF-first architecture.

- `backend/app/commands/handlers/object_create.py` — `handle_object_create()` accepts full IRI type values and mints object IRIs. Already works with any type IRI — no changes needed for user-created types.

- `backend/app/templates/forms/object_form.html` — Fully generic form renderer. Produces create/edit forms from any `NodeShapeForm`. User-created type forms will render automatically.

- `backend/app/templates/forms/_field.html` — Handles all field types: text, date, datetime, boolean, integer, decimal, URI, reference (search-as-you-type), dropdown (sh:in), multi-value. The generated SHACL shape just needs to use the right datatypes.

- `backend/app/templates/browser/ontology/tbox_tree.html` — Already has a `badge-user` CSS class for user-types namespace detection (`'user-types' in ns`). Classes in `urn:sempkm:user-types:` will get the "user" badge automatically.

- `backend/app/templates/browser/type_picker.html` — Lists types from `ShapesService.get_types()`. Once the FROM clause fix is in, user types appear here with no template changes.

- `backend/app/rdf/namespaces.py` — `COMMON_PREFIXES` dict used by `_resolve_predicate()` in object_create handler. User-created property IRIs should use known prefixes (dcterms, schema, foaf, skos, etc.) or the user-types namespace.

## Constraints

- **SHACL shape must be ShapesService-compatible:** The generated NodeShape must include `sh:targetClass`, `sh:property` blocks with `sh:path`, `sh:name`, and either `sh:datatype` or `sh:class`. These are the minimum attributes `_extract_property_shape()` requires. `sh:order` should be set for proper field ordering.

- **User-types graph is already in OntologyService FROM clauses:** Writing OWL class triples to `urn:sempkm:user-types` will make them visible in TBox immediately. No OntologyService changes needed.

- **No EventStore for class/shape creation:** Class creation is schema modification, not data modification. Writing directly to the triplestore via INSERT DATA (like gist loading) is appropriate. EventStore is for object-level operations.

- **Icon metadata can't go in manifest.yaml:** IconService reads from the filesystem. User-created types have no filesystem manifest. Need a triplestore-based icon storage approach — e.g., store `sempkm:typeIcon` and `sempkm:typeColor` as triples on the class IRI in `urn:sempkm:user-types`.

- **htmx patterns throughout:** All new UI must follow htmx partial rendering. No SPA framework components.

- **No advanced SHACL constraints:** Per D028, scope is name, icon, parent class, basic properties. No cardinality patterns, sh:pattern, conditional shapes, etc. Those are TYPE-03 (deferred).

- **Lucide icon names:** The project uses Lucide icons via CDN (`lucide@0.575.0`). Icon picker should offer a curated list of common Lucide icon names rather than the full 1400+ set.

## Common Pitfalls

- **ShapesService FROM clause omission** — If `urn:sempkm:user-types` is not added to `_fetch_shapes_graph()`, user-created shapes will be invisible to the form generation pipeline. This is the #1 integration risk. The fix is a single additional FROM clause line.

- **SHACL shape missing sh:name on properties** — `_extract_property_shape()` calls `_resolve_property_name()` which falls back to `_local_name()` from the path IRI. Relying on fallback is fragile — always generate explicit `sh:name` for each property shape.

- **Icon fallback to circle** — `IconService.get_type_icon()` returns `FALLBACK_ICON = "circle"` for unknown types. If icon metadata storage isn't implemented, user types will silently get circle icons everywhere. This is functional but ugly — prioritize icon storage.

- **IRI collision for user class names** — If two users create a class named "Task", the IRI `urn:sempkm:user-types:Task` collides. Mint IRIs with a UUID suffix or slugify with uniqueness check.

- **Property predicate IRI validation** — Users might enter invalid predicate IRIs. The form should offer a dropdown of common predicates (from installed model ontologies and well-known vocabularies) plus a custom IRI option with validation.

- **TBox cache staleness** — After creating a class, the TBox tree won't refresh automatically. Need an htmx trigger event (like `HX-Trigger: classCreated`) to refresh the ontology viewer.

## Open Risks

- **IconService extension complexity** — The current IconService is purely filesystem-based. Adding a SPARQL query fallback introduces an async dimension to what is currently a sync service. May need to refactor to async or use a hybrid approach (store icon metadata in a Python dict alongside the manifest cache, populated on class creation).

- **Property predicate UX** — Offering a good property predicate picker is non-trivial. Users need to choose between standard vocabulary predicates (dcterms:title, schema:name, etc.) and custom predicates. A bad UX here makes the feature unusable. Recommend: pre-populated dropdown with common predicates from installed models' RBox data + custom IRI input.

- **Delete/edit of user-created classes** — S08 scope is create-only per the roadmap. But if a user creates a broken class, there's no way to fix it. Consider adding at minimum a delete endpoint for user-created classes (DELETE triples from `urn:sempkm:user-types` where subject matches the class IRI).

- **ShapesService caching** — `_fetch_shapes_graph()` does a full CONSTRUCT query every time `get_node_shapes()` is called. With user types, the shapes graph changes more frequently. No caching exists currently — this is fine for now but may need attention if performance degrades.

## Skills Discovered

| Technology | Skill | Status |
|------------|-------|--------|
| SHACL | none found | no relevant skills available |
| RDF/OWL ontology | `sfc-gh-tjia/coco_skill_ontology@ontology-semantic-modeler` (11 installs) | available but low relevance — targets Snowflake semantic modeling, not RDF/SHACL |
| htmx | (installed: frontend-design skill covers web UI) | installed |

No skills worth installing for this slice. The domain is specialized (RDF/SHACL/OWL) and the codebase has all the patterns needed.

## Sources

- ShapesService integration: `backend/app/services/shapes.py` — `_fetch_shapes_graph()` at line 87 queries only model shapes graphs
- OntologyService USER_TYPES_GRAPH: `backend/app/ontology/service.py` — already included in `get_ontology_graph_iris()` at line 172
- SHACL shape reference: `models/basic-pkm/shapes/basic-pkm.jsonld` — complete NodeShape with property groups, ordering, datatypes, sh:in, sh:class references
- OWL class reference: `models/basic-pkm/ontology/basic-pkm.jsonld` — owl:Class + rdfs:label + rdfs:subClassOf pattern
- Form template: `backend/app/templates/forms/object_form.html` — generic SHACL-driven form renderer
- Type picker: `backend/app/templates/browser/type_picker.html` — uses `ShapesService.get_types()`
- Object creation: `backend/app/commands/handlers/object_create.py` — accepts full IRI types, no changes needed
- TBox badge for user types: `backend/app/templates/browser/ontology/tbox_tree.html` — `'user-types' in ns` check already present
- IconService: `backend/app/services/icons.py` — filesystem-only, needs extension for user types
- Lucide CDN: `backend/app/templates/base.html` line 43 — `lucide@0.575.0`
- Decisions: D027 (user-types graph), D028 (class creation scope), D055 (ontology viewer tabs)
