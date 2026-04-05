---
estimated_steps: 24
estimated_files: 2
skills_used: []
---

# T01: Add TTL caching to ShapesService

## Description

ShapesService currently re-fetches the entire shapes graph from the triplestore on EVERY call to `get_form_for_type()`, `get_node_shapes()`, `get_types()`, `get_labels_for_predicates()`, and `get_helptext_for_predicates()`. This means 2 SPARQL round-trips (1 SELECT for model IDs + 1 CONSTRUCT for shapes triples) plus rdflib parsing on every request. Since SHACL shapes only change when a Mental Model is installed/uninstalled (rare admin operation), this is pure waste.

Add a TTL-cached shapes graph to ShapesService so repeated calls return cached results. Also cache per-type form lookups.

## Steps

1. Read `backend/app/services/shapes.py` to understand the current structure — `_fetch_shapes_graph()` is the expensive method, called by `get_node_shapes()` which is called by `get_form_for_type()`, `get_types()`, etc.

2. Add `cachetools.TTLCache` dependency (already in pyproject.toml — used by LabelService). Add two caches:
   - `_shapes_graph_cache`: TTLCache(maxsize=1, ttl=600) storing the parsed rdflib Graph object. Key is a sentinel string like `'shapes'`.
   - `_form_cache`: TTLCache(maxsize=64, ttl=600) storing `NodeShapeForm` by type_iri.

3. Modify `_fetch_shapes_graph()` to check `_shapes_graph_cache` first. On miss, execute the existing SPARQL queries and cache the result. Log cache hit/miss at DEBUG level.

4. Modify `get_form_for_type()` to check `_form_cache[type_iri]` first. On miss, call `get_node_shapes()` (which uses the cached graph) and cache the found form.

5. Add a `clear_cache()` method that clears both caches. This will be called by model install/uninstall paths if needed (not wired in this task — shapes change rarely enough that TTL handles it).

6. Write tests in `backend/tests/test_shapes_cache.py`:
   - Test that repeated `get_form_for_type` calls with same type_iri only trigger 1 SPARQL CONSTRUCT (mock the client)
   - Test that `clear_cache()` forces a re-fetch
   - Test that cache expires after TTL

## Must-Haves

- [ ] `_fetch_shapes_graph()` uses TTLCache — second call within TTL returns cached Graph without SPARQL
- [ ] `get_form_for_type()` caches per type_iri — repeated calls for same type don't re-parse
- [ ] `clear_cache()` method exists and clears both caches
- [ ] DEBUG-level logging on cache hit/miss
- [ ] All existing tests still pass

## Verification

- `cd backend && python -m pytest tests/test_shapes_cache.py -v`
- `cd backend && python -m pytest tests/ -x --timeout=30` (no regressions)

## Inputs

- ``backend/app/services/shapes.py` — current ShapesService without caching`
- ``backend/app/services/labels.py` — reference implementation of TTLCache pattern`

## Expected Output

- ``backend/app/services/shapes.py` — ShapesService with TTL caching on _fetch_shapes_graph and get_form_for_type`
- ``backend/tests/test_shapes_cache.py` — unit tests proving cache hit/miss/expiry/clear behavior`

## Verification

cd backend && python -m pytest tests/test_shapes_cache.py -v && python -m pytest tests/ -x --timeout=60
