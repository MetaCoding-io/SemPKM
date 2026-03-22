---
estimated_steps: 5
estimated_files: 6
skills_used: []
---

# T03: Mirrored triples in object views and graph edges

**Slice:** S01 — Federated SPARQL & Mirrored Triples
**Milestone:** M033

## Description

Extend the object detail page and graph view to display mirrored triples from `urn:sempkm:mirrored` alongside user-created and inferred data. Mirrored triples get a distinct visual treatment — teal provenance badges on object properties and dotted teal edge lines in graph views — so users can immediately see which data came from external SPARQL endpoints.

This follows the exact pattern already established for inferred triples (purple dashed lines in graph, purple badges on properties). The implementation adds parallel query blocks, UNION clauses, and CSS styles.

## Steps

1. **Add mirrored property queries in `backend/app/browser/objects.py`:**
   - After the existing inferred-properties query block (lines ~119-145), add an identical block querying `GRAPH <urn:sempkm:mirrored>` for the object's properties. Store results in `mirrored_values` dict.
   - In the `read_values` merge section (lines ~226-235), add a loop for `mirrored_values` that appends entries with `"source": "mirrored"`.
   - Resolve labels for mirrored property IRIs (same pattern as `inferred_iris_to_resolve`).
   - Pass `mirrored_values` and `mirrored_labels` to the template context.

2. **Add mirrored edges in object graph query in `backend/app/browser/objects.py`:**
   - In the edge SPARQL query (lines ~479-519), add two more UNION blocks for mirrored graph — one for outgoing edges `{ GRAPH <urn:sempkm:mirrored> { <{iri}> ?p ?o ... } BIND("mirrored" AS ?source) }` and one for incoming edges.
   - In the source-checking code (line ~640), add handling for `source == "mirrored"` — return edge metadata with `"source": "mirrored"`.

3. **Add mirrored badge in `backend/app/templates/browser/object_read.html`:**
   - Find the existing inferred badge template block (look for `inferred-badge`). Add a parallel conditional for `source == "mirrored"` that renders a `.mirrored-badge` span with text "Mirrored" and a globe/external-link icon.

4. **Add mirrored CSS styles in `frontend/static/css/workspace.css`:**
   - Add `.mirrored-badge` styling parallel to `.inferred-badge` (lines ~3124-3157) but with teal/cyan color scheme (`var(--color-accent-teal, #14b8a6)` or similar).
   - Add `.prop-mirrored` row styling parallel to `.prop-inferred` (line ~5250).
   - Add `.mirrored-edge` style comment block.

5. **Add mirrored edge style in `frontend/static/js/graph.js` and update vocab prefix lists:**
   - In graph.js, find the existing `.inferred-edge` style definition (line ~78). Add a parallel entry for `.mirrored-edge` with `line-style: 'dotted'` and teal color (`#14b8a6`).
   - In graph.js edge building code (lines ~246-250), add a check for `edge.mirrored` to apply `mirrored-edge` class.
   - In `backend/app/sparql/router.py`, add `"urn:sempkm:mirror-prov:"` and `"urn:sempkm:mirrored:"` to `_VOCAB_PREFIXES` tuple.
   - In `frontend/static/js/sparql-console.js`, add `'urn:sempkm:mirror-prov:'` and `'urn:sempkm:mirrored:'` to `KNOWN_VOCAB_PREFIXES` array.

## Must-Haves

- [ ] Object detail page queries `GRAPH <urn:sempkm:mirrored>` and shows mirrored properties
- [ ] Mirrored properties tagged with `source: "mirrored"` in template context
- [ ] Mirrored badge renders with teal color and "Mirrored" text
- [ ] Graph edges from mirrored graph have dotted teal line style
- [ ] Mirrored namespace prefixes added to vocab exclusion lists (both backend and frontend)
- [ ] No regressions to existing inferred triple display

## Verification

- `rg "urn:sempkm:mirrored" backend/app/browser/objects.py` — at least 3 matches (property query, outgoing edges, incoming edges)
- `rg "mirrored-badge" frontend/static/css/workspace.css` — styling exists
- `rg "mirrored-edge" frontend/static/js/graph.js` — edge style exists
- `rg "mirror-prov" backend/app/sparql/router.py` — vocab prefix added

## Inputs

- `backend/app/browser/objects.py` — existing object detail with inferred triple pattern to extend
- `backend/app/templates/browser/object_read.html` — existing template with inferred badge
- `frontend/static/css/workspace.css` — existing styles with `.inferred-badge` pattern
- `frontend/static/js/graph.js` — existing graph with `.inferred-edge` style
- `backend/app/sparql/router.py` — `_VOCAB_PREFIXES` tuple to extend
- `frontend/static/js/sparql-console.js` — `KNOWN_VOCAB_PREFIXES` array to extend

## Expected Output

- `backend/app/browser/objects.py` — with mirrored property queries and edge UNION blocks
- `backend/app/templates/browser/object_read.html` — with mirrored badge conditional
- `frontend/static/css/workspace.css` — with `.mirrored-badge`, `.prop-mirrored` styles
- `frontend/static/js/graph.js` — with `.mirrored-edge` style and class application
- `backend/app/sparql/router.py` — with mirrored namespace in `_VOCAB_PREFIXES`
- `frontend/static/js/sparql-console.js` — with mirrored namespace in `KNOWN_VOCAB_PREFIXES`
