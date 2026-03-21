---
estimated_steps: 5
estimated_files: 2
---

# T01: Fix model_shapes_loader to include rules graphs and pass advanced=True in ValidationService

**Slice:** S01 — Validation Pipeline Fix & Performance Measurement
**Milestone:** M030

## Description

The validation pipeline has two broken links that prevent all SHACL-AF SPARQLConstraint rules from firing:

1. **`model_shapes_loader()`** in `backend/app/services/models.py` (line ~498) only fetches shapes graphs (`urn:sempkm:model:{id}:shapes`) via SPARQL CONSTRUCT. It does NOT fetch rules graphs (`urn:sempkm:model:{id}:rules`). The SPARQLConstraint validation rules (overdue tasks, stale contacts, unprocessed notes, etc.) live in rules files loaded into rules graphs at model install time — they are never passed to pyshacl.

2. **`ValidationService.validate()`** in `backend/app/services/validation.py` (line ~98-104) calls `pyshacl.validate()` WITHOUT `advanced=True`. Without this flag, pyshacl ignores SHACL-AF features (SPARQLRule, SPARQLConstraint). The inference service (`backend/app/inference/service.py` lines 144, 157) correctly passes `advanced=True` — the validation service must match.

Both fixes must be applied together. Fixing only the loader still produces zero results because `advanced=True` is missing. Fixing only the flag still produces zero results because rules triples aren't in the shapes graph.

## Steps

1. Open `backend/app/services/models.py` and find the `model_shapes_loader()` function (async, near bottom of file). Currently it:
   - Queries model registry for installed model IDs
   - Builds CONSTRUCT with FROM clauses for `urn:sempkm:model:{model_id}:shapes` only
   - Returns a single rdflib Graph

2. Add a second CONSTRUCT query for rules graphs. After the shapes CONSTRUCT, build a similar query with FROM clauses for `urn:sempkm:model:{model_id}:rules`. Execute it, parse the result, and merge into the shapes graph via `shapes_graph += rules_graph` (rdflib's Graph.__iadd__ merges triples). Update the log message to show both counts:
   ```python
   logger.info("Loaded %d shapes + %d rules triples from %d model(s)", 
               len(shapes_graph) - rules_count, rules_count, len(bindings))
   ```
   Track rules_count by checking `len(rules_graph)` before merging.

3. Open `backend/app/services/validation.py` and find the `pyshacl.validate()` call inside `ValidationService.validate()` (line ~99-104). Currently:
   ```python
   conforms, results_graph, _results_text = await asyncio.to_thread(
       pyshacl.validate,
       data_graph,
       shacl_graph=shapes_graph,
       allow_infos=True,
       allow_warnings=True,
   )
   ```
   Add `advanced=True` to the kwargs:
   ```python
   conforms, results_graph, _results_text = await asyncio.to_thread(
       pyshacl.validate,
       data_graph,
       shacl_graph=shapes_graph,
       allow_infos=True,
       allow_warnings=True,
       advanced=True,
   )
   ```

4. Verify no other callers of `model_shapes_loader` are affected — check with `grep -rn "model_shapes_loader\|shapes_loader" backend/app/`. The function is called only from `main.py:shapes_loader()` wrapper.

5. Run existing tests to ensure no regressions: `cd backend && .venv/bin/pytest tests/ -x -q`

## Must-Haves

- [ ] `model_shapes_loader()` builds FROM clauses for BOTH `urn:sempkm:model:{id}:shapes` AND `urn:sempkm:model:{id}:rules`
- [ ] Rules triples merged into the returned Graph
- [ ] `pyshacl.validate()` called with `advanced=True`
- [ ] Log message updated to show shapes + rules triple counts
- [ ] Existing tests still pass

## Verification

- `grep -n "advanced" backend/app/services/validation.py` shows `advanced=True` in the pyshacl.validate call
- `grep -n "rules" backend/app/services/models.py` shows rules graph loading in model_shapes_loader
- `cd backend && .venv/bin/pytest tests/ -x -q` — existing tests pass (no regressions)

## Inputs

- `backend/app/services/models.py` — contains `model_shapes_loader()` function (~line 498). Currently fetches shapes only.
- `backend/app/services/validation.py` — contains `ValidationService.validate()` method (~line 52). Currently lacks `advanced=True`.
- `backend/app/inference/service.py` — reference implementation showing `advanced=True` at lines 144, 157. Match this pattern.

## Expected Output

- `backend/app/services/models.py` — `model_shapes_loader()` updated to fetch and merge rules graphs
- `backend/app/services/validation.py` — `validate()` updated with `advanced=True`

## Observability Impact

- **Changed signal:** `model_shapes_loader` log line changes from `"Loaded %d shapes triples from %d model(s)"` to `"Loaded %d shapes + %d rules triples from %d model(s)"`. Agents and operators can inspect Docker API logs for this line to confirm rules triples are being loaded (non-zero rules count = rules are feeding into validation).
- **How to inspect:** `docker compose logs api 2>&1 | grep "shapes.*rules triples"` — shows shapes and rules triple counts per startup/reload.
- **Failure state:** If rules count is 0 but shapes count is >0, rules graphs are missing from the triplestore (model install issue). If both are 0, no models are installed. If the lint panel shows 0 warnings on objects that should violate rules, check this log line first.
- **`advanced=True` flag:** No runtime log for this — verify via code grep: `grep -n "advanced=True" backend/app/services/validation.py`.
