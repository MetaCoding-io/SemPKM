# S02: Hierarchy Explorer Mode — Research

**Date:** 2026-03-12

## Summary

S02 replaces the hierarchy mode placeholder with a working `dcterms:isPartOf`-based tree in the explorer. The infrastructure from S01 (mode dropdown, `EXPLORER_MODES` registry, `#explorer-tree-body` swap target, handler dispatch pattern) is complete and well-tested — this slice only needs to implement the actual hierarchy handler, a lazy children endpoint, SPARQL queries, and a new template.

The work is straightforward because `dcterms:isPartOf` is a standard Dublin Core predicate already in the registered prefix set (`COMMON_PREFIXES` includes `dcterms:`), and the existing tree node/leaf HTML+CSS patterns from `nav_tree.html` / `tree_children.html` can be directly reused for hierarchy rendering. The main challenge is handling objects without `isPartOf` (root objects), lazy expansion of children at arbitrary depth, and proper icon resolution for mixed-type hierarchy nodes.

Currently **no objects in the codebase have `dcterms:isPartOf` triples** — neither the basic-pkm model ontology, seed data, nor any existing code references this predicate. The hierarchy mode will show an empty tree until users assign parent relationships. This is expected and documented in the roadmap.

## Recommendation

**Implement in 3-4 small tasks:**

1. **SPARQL queries + handler**: Write two SPARQL queries — one for root objects (those with no `dcterms:isPartOf` triple), one for children of a given parent IRI. Replace the `_handle_hierarchy` placeholder with a real handler that queries roots and renders them. Add a new endpoint `GET /browser/explorer/children?parent={iri}` for lazy child expansion.

2. **Templates**: Create `hierarchy_tree.html` (root-level rendering) and `hierarchy_children.html` (child nodes for lazy expansion). Reuse the existing `.tree-node` / `.tree-leaf` CSS classes — hierarchy nodes that have children get the expandable `.tree-node` pattern with `hx-trigger="click once"`, leaf nodes get `.tree-leaf`.

3. **Backend unit tests**: Test the SPARQL queries return correct results for root objects and children, test handler dispatch, test the children endpoint validation.

4. **E2E tests**: Update the existing explorer mode E2E tests to verify hierarchy mode shows real content (when data exists) or an appropriate empty state.

**Key design decisions needed:**
- Hierarchy nodes should be expandable `.tree-node` elements (like type nodes in by-type mode), not leaf elements — because any object could have children
- The children endpoint needs to know the parent IRI and return both the parent's direct children AND indicate which children themselves have children (so the toggle arrow can be shown)
- Objects with no `dcterms:isPartOf` are roots; objects whose `dcterms:isPartOf` target doesn't exist in the graph are also roots

## Don't Hand-Roll

| Problem | Existing Solution | Why Use It |
|---------|------------------|------------|
| Tree node expand/collapse CSS | `.tree-node` / `.tree-toggle` / `.tree-children` classes in `workspace.css` | Battle-tested expand/collapse with rotate animation; `.tree-node.expanded + .tree-children` display logic |
| Lazy child loading via htmx | `hx-trigger="click once"` pattern in `nav_tree.html` | Identical pattern — click node, load children into target div, one-shot trigger |
| Label resolution | `LabelService.resolve_batch()` | Standard label resolution with precedence: dcterms:title > rdfs:label > skos:prefLabel > etc. |
| Icon resolution | `IconService.get_type_icon()` | Returns type-specific icons from installed models |
| Object click-to-open | `handleTreeLeafClick()` in `workspace.js` | Same onclick handler used by by-type tree leaves — opens object tab |
| Mode handler registration | `EXPLORER_MODES` dict in `workspace.py` | Handler already registered as `"hierarchy"` — just replace the implementation |
| IRI validation | `_validate_iri()` from `_helpers.py` | Already used by `tree_children` endpoint for IRI param validation |
| SPARQL prefix injection | `inject_prefixes()` from `sparql/client.py` | Auto-adds `dcterms:` and other common prefixes to queries |
| Triplestore access | `request.app.state.triplestore_client` | Standard pattern used by `tree_children` endpoint |

## Existing Code and Patterns

- `backend/app/browser/workspace.py` — `EXPLORER_MODES` registry (line 80), `_handle_hierarchy` placeholder (line 52), `explorer_tree` endpoint (line 150), `tree_children` endpoint (line 177) as reference for lazy expansion pattern
- `backend/app/templates/browser/nav_tree.html` — Reference template for tree nodes with htmx lazy loading; pattern: `.tree-node[hx-get][hx-trigger="click once"][hx-target]` → `.tree-children` container
- `backend/app/templates/browser/tree_children.html` — Reference template for leaf nodes; pattern: `.tree-leaf[data-iri][onclick="handleTreeLeafClick(...)"]` with drag support
- `frontend/static/css/workspace.css` (lines 212-320) — All `.tree-*` CSS classes: `.tree-node`, `.tree-toggle`, `.tree-children`, `.tree-leaf`, `.tree-label`, `.tree-empty`; expand/collapse via `.tree-node.expanded + .tree-children { display: block }`
- `backend/app/rdf/namespaces.py` — `COMMON_PREFIXES` includes `"dcterms": "http://purl.org/dc/terms/"`, `CURRENT_GRAPH_IRI = URIRef("urn:sempkm:current")`
- `backend/app/services/labels.py` — `LabelService.resolve_batch(iris)` for batch label resolution
- `backend/app/services/icons.py` — `IconService.get_type_icon(type_iri, context)` for per-type icons
- `backend/app/dependencies.py` — `get_triplestore_client`, `get_label_service` FastAPI dependency injection
- `backend/tests/test_explorer_modes.py` — 8 existing unit tests for mode registry; need updating when handler changes from placeholder to real implementation
- `e2e/tests/19-explorer-modes/explorer-mode-switching.spec.ts` — 5 E2E tests; hierarchy test currently expects placeholder content (must update)
- `e2e/helpers/selectors.ts` — `SEL.explorer.*` selectors for mode testing
- `backend/app/browser/workspace.py` tree_children endpoint (line 177) — SPARQL pattern: `GRAPH <urn:sempkm:current> { ?obj rdf:type <{type_iri}> . }` with label resolution and icon lookup

## Constraints

- **All objects live in `urn:sempkm:current` graph** — All SPARQL queries must scope to `GRAPH <urn:sempkm:current> { ... }` for user data
- **No `dcterms:isPartOf` data exists yet** — The hierarchy tree will be empty on a fresh install with seed data. Must handle empty state gracefully with a meaningful message (not just "No models installed")
- **`dcterms:isPartOf` uses a full IRI** — The predicate is `<http://purl.org/dc/terms/isPartOf>`, registered as `dcterms:isPartOf` in SPARQL via `COMMON_PREFIXES`
- **Frontend is htmx + vanilla JS only** — No React. All rendering via Jinja2 templates + htmx partials
- **Auth rate limit in E2E: 5 tests per spec file** — Cannot add more than 5 tests in a single spec file without hitting the magic-link rate limit
- **Tree node click toggles expand/collapse** — The `.tree-node` click handler toggles `.expanded` class; htmx `click once` fires only on first click. Subsequent clicks just toggle CSS visibility
- **Objects can have multiple types** — An object in the hierarchy could be any type. Icons should reflect the object's `rdf:type`, not assume a single type
- **Each hierarchy node needs a unique DOM id** — For htmx `hx-target` to work, each node's children container needs a unique `id` attribute (same pattern as `children-{{ safe_id }}` in nav_tree.html)
- **`handleTreeLeafClick` requires `data-iri` attribute** — Leaf click handler reads `data-iri` from the element

## Common Pitfalls

- **Root objects query must use FILTER NOT EXISTS, not OPTIONAL** — To find objects with no `dcterms:isPartOf`, use `FILTER NOT EXISTS { ?obj dcterms:isPartOf ?parent . }`. Using `OPTIONAL` + `FILTER(!BOUND(?parent))` is less efficient and can produce duplicates if the object has multiple types.

- **Mixed parent/leaf nodes** — In a hierarchy, any node could be both a parent (has children) and a leaf (is clickable). The template needs to support click-to-open behavior AND expandable children. Solution: render all hierarchy nodes as expandable `.tree-node` elements that also support `handleTreeLeafClick` on a label click, or detect which nodes have children via a sub-query.

- **Circular `isPartOf` chains** — If A isPartOf B and B isPartOf A, lazy expansion would loop forever. The backend doesn't need to detect this (lazy loading naturally stops when the user stops expanding), but infinite nesting should be documented as a data quality issue, not a code bug.

- **Empty hierarchy message** — When no objects have `isPartOf` relationships, the hierarchy mode should show a helpful message like "No hierarchy relationships found. Set dcterms:isPartOf on objects to organize them hierarchically." — not the generic "No objects" or "Coming soon" placeholder.

- **Performance with large hierarchies** — The root query should only fetch root objects (no parent), not all objects. The children endpoint loads one level at a time. This lazy pattern avoids loading the entire hierarchy tree at once.

- **Type icon for hierarchy nodes** — Unlike by-type mode where all children share the type node's icon, hierarchy mode has mixed-type children. Each node needs its own icon resolved from its `rdf:type`. This requires querying both the object IRI, label, AND type in the SPARQL query, then looking up the icon per-type.

- **Child count indicator** — Consider whether to show a count badge on hierarchy nodes indicating how many children they have. This is a nice-to-have but adds SPARQL complexity. Recommend skipping for first pass.

## Open Risks

- **No existing seed data with `dcterms:isPartOf`** — Testing the hierarchy mode requires creating objects with parent relationships first. E2E tests will need to either create test data with `isPartOf` triples or verify the empty state only. Creating test data requires the object create API to support setting arbitrary predicates including object properties (links to other objects), which may not be straightforward via the form-based create flow.

- **Detecting "has children" for toggle display** — To show the expand toggle (▶) only on nodes that actually have children, we'd need a sub-query or a separate ASK query per node. Alternative: always show the toggle, and if the children endpoint returns empty, show "No children" in the expanded area. This is simpler and matches the lazy-loading philosophy.

- **Setting `dcterms:isPartOf` via the UI** — Users need a way to set parent relationships on objects. This might require the object edit form to support object property fields (dropdowns selecting other objects). If the SHACL shapes don't define `dcterms:isPartOf` as a property, it won't appear in the edit form. This is outside S02's scope but worth noting — hierarchy mode is only useful if users can create hierarchy relationships.

## Skills Discovered

| Technology | Skill | Status |
|------------|-------|--------|
| htmx | `mindrally/skills@htmx` (198 installs) | available — not needed, patterns well-established in codebase |
| SPARQL/RDF | `letta-ai/skills@sparql-university` (36 installs) | available — not needed, SPARQL patterns well-established in codebase |
| FastAPI | `wshobson/agents@fastapi-templates` (6.2K installs) | available — not needed, FastAPI patterns well-established in codebase |

No skills recommended for installation — the codebase has strong established patterns for all three technologies. The htmx tree rendering, SPARQL querying, and FastAPI endpoint patterns from S01 and the existing by-type mode provide complete reference implementations.

## Sources

- S01 task summaries (T01-T04) — established explorer mode infrastructure, handler registry, E2E test patterns
- `backend/app/browser/workspace.py` — current `_handle_hierarchy` placeholder and `tree_children` reference endpoint
- `backend/app/templates/browser/nav_tree.html` — htmx lazy-loading tree node template pattern
- `frontend/static/css/workspace.css` — `.tree-*` CSS class hierarchy for expand/collapse behavior
- `backend/app/rdf/namespaces.py` — `dcterms` prefix registration in `COMMON_PREFIXES`
- Dublin Core Terms specification: `dcterms:isPartOf` — standard predicate for part-whole relationships (source: [Dublin Core DCMI Terms](https://www.dublincore.org/specifications/dublin-core/dcmi-terms/#isPartOf))
