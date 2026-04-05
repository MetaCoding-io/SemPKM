# S01: Query Optimization & Caching — UAT

**Milestone:** M049
**Written:** 2026-04-05T20:18:32.934Z

# S01 UAT: Query Optimization & Caching

## Preconditions

- Backend running with RDF4J triplestore and at least one Mental Model installed (basic-pkm)
- At least 3 objects of different types exist in the triplestore
- Backend logs visible (docker compose logs -f api or terminal output)

## Test 1: UNION Query — Single SPARQL for Properties

**Steps:**
1. Set backend log level to DEBUG
2. Open an object tab in the workspace (e.g., click a Project in the explorer)
3. Inspect backend logs for the get_object handler

**Expected:**
- Exactly 1 SPARQL query containing `UNION` with three graph patterns (current, inferred, mirrored)
- No separate queries for `urn:sempkm:inferred` or `urn:sempkm:mirrored` graphs
- Object properties, inferred properties, and mirrored properties all render correctly in the object view

## Test 2: Label Consolidation — Single Batch

**Steps:**
1. Open an object that has relations to other objects (e.g., a Project with linked People)
2. Inspect backend logs for `resolve_batch` calls

**Expected:**
- Exactly 1 `resolve_batch` call per get_object invocation (not 5)
- All labels render correctly — type labels, property labels, related object labels

## Test 3: ShapesService Caching

**Steps:**
1. Open an object tab (first load after server start)
2. Check backend DEBUG logs for shapes cache messages
3. Open a second object of the same type
4. Check backend DEBUG logs again

**Expected:**
- First load: "Shapes graph cache MISS" message
- Second load: "Shapes graph cache HIT" message
- Form fields render identically on both loads

## Test 4: asyncio.gather Parallelization — Timing Improvement

**Steps:**
1. Open 5 different objects in sequence, each in a new tab
2. Check backend logs for timing messages of format: `get_object <iri> completed in X.XXXs`

**Expected:**
- Each object load completes in under 1.5 seconds (wall-clock logged time)
- Timing is consistent across different object types
- No errors or exceptions in the log output

## Test 5: Deduplication Correctness

**Steps:**
1. Open an object that has both user-asserted and inferred properties (e.g., after running SHACL-AF rules that infer new triples)
2. Check the read-mode object view

**Expected:**
- User-asserted values display in the main properties section
- Inferred values display in the inferred section (not duplicated in main)
- No duplicate property values visible

## Test 6: Cache Invalidation on Model Change

**Steps:**
1. Open an object to warm the shapes cache
2. Uninstall the Mental Model via admin portal
3. Reinstall the Mental Model
4. Open an object of that model's type

**Expected:**
- After reinstall, forms render correctly (cache expires within 600s TTL)
- No stale form fields from pre-uninstall shapes

## Edge Cases

### E1: Object with no inferred/mirrored properties
- Open a freshly created object with only user-asserted properties
- Expected: UNION query returns only "user" source rows, inferred/mirrored sections are empty, no errors

### E2: Object with many relations (20+ edges)
- Open an object with many outbound/inbound edges
- Expected: Single label batch resolves all relation IRIs, no timeout or truncation

### E3: Concurrent object tab opens
- Rapidly open 3+ object tabs in quick succession
- Expected: Each tab loads independently, no race conditions in shapes cache access
