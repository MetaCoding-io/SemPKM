# S01: Query Optimization & Caching

**Goal:** Object tab loads in under 1.5 seconds by eliminating the sequential SPARQL query waterfall in `get_object`: cache ShapesService results, combine multi-graph property queries into a single UNION, consolidate 5 label batches into 1, and parallelize independent awaits with asyncio.gather.
**Demo:** After this: Open 5 different objects in the browser. Each tab loads in under 1.5 seconds (Network tab timing). Before/after timing comparison captured.

## Tasks
- [x] **T01: ShapesService TTL caching already implemented — verified 12 cache tests pass with zero regressions; fixed missing icalendar dev dependency** — ## Description

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
  - Estimate: 45m
  - Files: backend/app/services/shapes.py, backend/tests/test_shapes_cache.py
  - Verify: cd backend && python -m pytest tests/test_shapes_cache.py -v && python -m pytest tests/ -x --timeout=60
- [x] **T02: Replaced 3 sequential SPARQL property queries with 1 UNION query and consolidated 5 label batch calls into 1 in get_object handler** — ## Description

The `get_object` handler in `backend/app/browser/objects.py` makes 3 separate SPARQL queries to fetch properties from current, inferred, and mirrored graphs — each is a sequential HTTP round-trip to RDF4J. It also makes up to 5 separate `label_service.resolve_batch()` calls sequentially.

Combine the 3 property queries into 1 UNION query (similar to how `get_relations` already uses UNION). Consolidate the 5 label batches into 1 combined batch after all IRIs are known.

## Steps

1. Read `backend/app/browser/objects.py` lines 100-310 (the `get_object` handler) to understand the current query sequence.

2. Replace the 3 separate property queries (props_sparql, inferred_props_sparql, mirrored_props_sparql) with a single UNION query that annotates each result with its source graph:
   ```sparql
   SELECT ?p ?o ?source WHERE {
     { GRAPH <urn:sempkm:current> { <IRI> ?p ?o } BIND("user" AS ?source) }
     UNION
     { GRAPH <urn:sempkm:inferred> { <IRI> ?p ?o } BIND("inferred" AS ?source) }
     UNION
     { GRAPH <urn:sempkm:mirrored> { <IRI> ?p ?o } BIND("mirrored" AS ?source) }
   }
   ```

3. Adjust the binding-processing logic to partition results by `?source` into `values`, `inferred_values`, and `mirrored_values` dicts (same structure as before). Preserve the existing deduplication logic (user > inferred > mirrored).

4. After all property processing and form resolution is done, collect ALL IRIs that need labels into a single set: ref_iris + type_class_iris + object/type iris + inferred iris + mirrored iris. Make ONE call to `label_service.resolve_batch(all_iris)`. Then extract sub-results from the single response dict.

5. Write a focused test in `backend/tests/test_object_query_opt.py` that mocks `TriplestoreClient.query` and `LabelService.resolve_batch`, calls a simplified version of the query logic, and asserts:
   - Only 1 SPARQL query is made for properties (not 3)
   - Only 1 label batch call is made (not 5)
   - Output structure (values, inferred_values, mirrored_values) is identical to the old behavior

## Must-Haves

- [ ] Single UNION query replaces 3 separate graph queries
- [ ] Single label batch replaces 5 separate batches
- [ ] Deduplication logic preserved: user values take precedence over inferred/mirrored
- [ ] Template context structure unchanged — no template modifications needed
- [ ] Test verifies query count reduction and output equivalence

## Verification

- `cd backend && python -m pytest tests/test_object_query_opt.py -v`
- `cd backend && python -m pytest tests/ -x --timeout=30` (no regressions)
  - Estimate: 1h
  - Files: backend/app/browser/objects.py, backend/tests/test_object_query_opt.py
  - Verify: cd backend && python -m pytest tests/test_object_query_opt.py -v && python -m pytest tests/ -x --timeout=60
- [x] **T03: Parallelized SPARQL property query and SQLite favorites check via asyncio.gather, added wall-clock timing log** — ## Description

After T01 (cached shapes) and T02 (combined queries + consolidated labels), the `get_object` handler still has independent async operations that run sequentially. The UNION property query, the ShapesService form lookup (now cached), and the favorites SQLite check are all independent and can run concurrently.

Add `asyncio.gather` to parallelize these independent operations. Also add timing instrumentation that logs the total handler wall-clock time so we can measure the improvement.

## Steps

1. Read the modified `backend/app/browser/objects.py` (output of T02) to identify the current sequential flow.

2. Identify the independent operation groups that can run concurrently:
   - Group A: UNION property query (depends on decoded_iri only)
   - Group B: Favorites SQLite query (depends on decoded_iri + user.id only)
   These two are independent. The shapes lookup needs type_iris from Group A, so it stays sequential after Group A. But the label batch (from T02) also needs type_iris. So the parallel groups are:
   - Phase 1 (parallel): property UNION query + favorites check
   - Phase 2 (sequential, needs property results): shapes form lookup
   - Phase 3 (sequential, needs form + properties): consolidated label batch

3. Wrap Phase 1 in `asyncio.gather`:
   ```python
   import asyncio
   props_result, fav_result = await asyncio.gather(
       client.query(union_sparql),
       db.execute(fav_query),
   )
   ```

4. Add timing instrumentation at the top and bottom of `get_object`:
   ```python
   import time
   _start = time.perf_counter()
   # ... handler body ...
   _elapsed = time.perf_counter() - _start
   logger.info("get_object %s completed in %.3fs", decoded_iri, _elapsed)
   ```

5. Write a test in `backend/tests/test_object_parallel.py` that:
   - Mocks the triplestore client and db session with artificial delays (e.g. 0.1s each)
   - Verifies that get_object with asyncio.gather completes faster than the sum of individual delays
   - Verifies that the timing log message is emitted

## Must-Haves

- [ ] Property query and favorites check run concurrently via asyncio.gather
- [ ] Handler logs wall-clock time at INFO level
- [ ] No change to template context or response structure
- [ ] Test proves parallel execution reduces total time

## Verification

- `cd backend && python -m pytest tests/test_object_parallel.py -v`
- `cd backend && python -m pytest tests/ -x --timeout=30` (no regressions)
- Manual: open an object tab in the browser, check backend logs for timing output
  - Estimate: 45m
  - Files: backend/app/browser/objects.py, backend/tests/test_object_parallel.py
  - Verify: cd backend && python -m pytest tests/test_object_parallel.py -v && python -m pytest tests/ -x --timeout=60
