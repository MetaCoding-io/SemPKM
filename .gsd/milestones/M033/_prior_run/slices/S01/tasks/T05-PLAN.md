---
estimated_steps: 5
estimated_files: 6
skills_used: []
---

# T05: Mirrored triple indicators on object pages and comprehensive test suite

**Slice:** S01 — Federated SPARQL & Mirrored Triples
**Milestone:** M033

## Description

Mirrored triples must be visually distinct from user-created and inferred data. The object page already displays inferred triples with `.inferred-badge` styling and `source: "inferred"` tagging — mirrored triples follow this exact pattern with a distinct visual treatment.

The object page's `object_read_page()` in `backend/app/browser/objects.py` already queries `GRAPH <urn:sempkm:inferred>` separately and merges results into `read_values` tagged with `source: "inferred"`. We add a parallel query for `GRAPH <urn:sempkm:mirrored>` tagged with `source: "mirrored"`, plus a provenance query to get the source endpoint for each mirrored property.

The frontend (`workspace.js`) renders properties based on their `source` field — `"inferred"` gets the inferred badge. We add a `"mirrored"` branch with a different badge showing the source endpoint as a tooltip.

The graph view (`graph.js`) already has `.inferred-edge` (dashed lines). We add `.mirrored-edge` (dotted lines, different color).

This task also writes the comprehensive integration-level tests validating the full mirror flow.

## Steps

1. **Extend objects.py with mirrored graph query:** In `object_read_page()`, after the existing inferred properties query, add a parallel query against `GRAPH <urn:sempkm:mirrored>` for the object's IRI. Tag results with `source: "mirrored"`. Also query provenance: for each mirrored predicate-value pair, find the mirror batch it belongs to and extract `dcterms:source` (the endpoint URL). Attach `source_endpoint` to each mirrored value dict. Merge into `read_values` alongside user and inferred data.

2. **Add mirrored badge rendering in workspace.js:** In the property rendering code (where `source === 'inferred'` triggers the inferred badge), add a branch for `source === 'mirrored'`. Render a `.mirrored-badge` element with a "cloud-download" Lucide icon (or "globe" to indicate external source). If `source_endpoint` is available, show it as a tooltip on hover. The badge text can be "Mirrored" or the endpoint hostname for brevity.

3. **Add mirrored CSS styles in workspace.css:** Define `.mirrored-badge` following the `.inferred-badge` pattern but with a distinct color scheme (teal/blue vs inferred's purple/violet). Also define `.prop-mirrored` for the property row styling (subtle background tint). Define `.mirrored-stale` for future use (when TTL is added).

4. **Add mirrored edge style in graph.js:** After the existing `.inferred-edge` selector style definition (dashed edges), add a `.mirrored-edge` selector with dotted `line-style`, a distinct color (teal), and slightly different opacity. In the edge data building code, check if an edge comes from the mirrored graph and apply the `mirrored-edge` class (same pattern as `inferred-edge`). Add `urn:sempkm:mirror:` to the `KNOWN_VOCAB_PREFIXES` array in sparql-console.js.

5. **Write comprehensive test suite:** Add/extend `backend/tests/test_mirror_service.py` with:
   - Test MirrorService.mirror_results() produces valid Turtle with provenance triples
   - Test binding-to-triple conversion handles URI-URI, URI-Literal, typed literals, language tags
   - Test provenance metadata includes source endpoint, timestamp, query hash
   - Test empty bindings produce no triples (graceful no-op)
   - Test get_mirror_batches() returns batch metadata
   - Test delete_mirror_batch() removes triples
   - Test scope_to_current_graph() with include_mirrored=True includes urn:sempkm:mirrored in FROM
   - Verify `urn:sempkm:mirror:` in _VOCAB_PREFIXES in router.py (simple import test)

## Must-Haves

- [ ] Object page queries urn:sempkm:mirrored and tags values with `source: "mirrored"`
- [ ] Provenance (source endpoint) attached to mirrored property values
- [ ] `.mirrored-badge` renders with distinct teal/blue color, tooltip shows endpoint
- [ ] `.mirrored-edge` in graph view uses dotted line style
- [ ] `urn:sempkm:mirror:` in KNOWN_VOCAB_PREFIXES (frontend)
- [ ] Comprehensive test suite for MirrorService covers binding conversion, provenance, CRUD
- [ ] All tests pass: `tests/test_mirror_service.py` and `tests/test_sparql_client.py`

## Verification

- `cd backend && .venv/bin/python -m pytest tests/test_mirror_service.py tests/test_sparql_client.py -v` — all pass
- `grep -q "mirrored-badge" frontend/static/css/workspace.css` — CSS exists
- `grep -q "mirrored-edge" frontend/static/js/graph.js` — graph style exists
- `grep -q "source.*mirrored" backend/app/browser/objects.py` — source tagging exists

## Inputs

- `backend/app/browser/objects.py` — existing object_read_page() with inferred properties pattern
- `frontend/static/js/workspace.js` — existing property rendering with source-based badges
- `frontend/static/css/workspace.css` — existing .inferred-badge styles
- `frontend/static/js/graph.js` — existing .inferred-edge style
- `frontend/static/js/sparql-console.js` — KNOWN_VOCAB_PREFIXES array
- `backend/app/federation/mirror_service.py` — MirrorService class (from T03)
- `backend/tests/test_mirror_service.py` — existing tests from T03 to extend

## Expected Output

- `backend/app/browser/objects.py` — mirrored graph query and source tagging added
- `frontend/static/js/workspace.js` — mirrored badge rendering
- `frontend/static/css/workspace.css` — .mirrored-badge, .prop-mirrored, .mirrored-stale styles
- `frontend/static/js/graph.js` — .mirrored-edge style definition and class assignment
- `frontend/static/js/sparql-console.js` — urn:sempkm:mirror: added to KNOWN_VOCAB_PREFIXES
- `backend/tests/test_mirror_service.py` — comprehensive test suite (8+ test cases)

## Observability Impact

- **New signals:** Mirrored triple source tagging in object page `read_values` dict (`source: "mirrored"`, `source_endpoint: "<url>"`). Graph edge JSON includes `mirrored: true/false` flag.
- **Inspection:** On any object page, mirrored properties show teal `.mirrored-badge` with tooltip containing the federation endpoint hostname. In graph view, mirrored edges render as dotted teal lines. Edge provenance popover for mirrored edges shows "Mirrored from <endpoint>" with timestamp.
- **Failure visibility:** If mirrored graph query fails, `logger.warning` is emitted with the object IRI. If provenance query fails, mirrored values still display but with empty `source_endpoint`. The UI gracefully falls back to "external endpoint" label.
- **Diagnostic queries:** `GRAPH <urn:sempkm:mirrored> { <object_iri> ?p ?o }` returns mirrored properties for any object. `?batch a prov:Entity . ?batch dcterms:source ?source` in the mirrored graph returns provenance.
