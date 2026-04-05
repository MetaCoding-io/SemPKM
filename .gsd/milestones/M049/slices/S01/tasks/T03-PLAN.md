---
estimated_steps: 41
estimated_files: 2
skills_used: []
---

# T03: Parallelize independent work in get_object with asyncio.gather and add timing log

## Description

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

## Inputs

- ``backend/app/browser/objects.py` — output of T02 with UNION query and consolidated labels`
- ``backend/app/services/shapes.py` — output of T01 with TTL caching`

## Expected Output

- ``backend/app/browser/objects.py` — get_object with asyncio.gather parallelization and timing log`
- ``backend/tests/test_object_parallel.py` — tests proving parallel execution and timing instrumentation`

## Verification

cd backend && python -m pytest tests/test_object_parallel.py -v && python -m pytest tests/ -x --timeout=60
