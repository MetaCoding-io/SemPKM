---
estimated_steps: 5
estimated_files: 1
---

# T03: Fix source_model attribution with multiple models via GRAPH pattern

**Slice:** S02 — Correctness Fixes
**Milestone:** M002

## Description

`get_all_view_specs()` in `views/service.py` builds FROM clauses for all model view graphs and runs a single merged SPARQL query, then sets `source_model=model_ids[0] if len(model_ids) == 1 else ""`. With 2+ models installed, every spec gets an empty `source_model`, breaking type-switching, deduplication logic, and grouping in the views index page.

The fix replaces the FROM-clause approach with a `GRAPH ?g { ... }` pattern that captures which named graph each spec lives in. A reverse map from `urn:sempkm:model:{id}:views` → `{id}` enables setting the correct `source_model` per spec.

## Steps

1. Read `backend/app/views/service.py` lines 125-200 to confirm the exact query structure and the `source_model` assignment
2. Build a reverse map dict: `graph_to_model = {f"urn:sempkm:model:{mid}:views": mid for mid in model_ids}` after collecting model IDs
3. Rewrite the specs SPARQL query to use `GRAPH ?g { ... }` instead of FROM clauses, selecting `?g` as an additional binding:
   - Use a VALUES clause to constrain `?g` to only the model view graph IRIs (prevents scanning unrelated graphs)
   - Add `?g` to the SELECT variables
4. Update the spec construction loop to extract `?g` binding and look up `source_model` via `graph_to_model.get(g_value, "")`
5. Verify: Docker build succeeds, structural check of the new SPARQL, and existing E2E tests pass

## Must-Haves

- [ ] SPARQL query uses `GRAPH ?g { ... }` pattern instead of FROM clauses
- [ ] `?g` is selected and bound to the model views graph IRI per spec
- [ ] Reverse map correctly extracts model ID from graph IRI `urn:sempkm:model:{id}:views`
- [ ] Each `ViewSpec.source_model` is set to the correct model ID string, not empty string
- [ ] Single-model case still works correctly (backward compatible)
- [ ] Zero-model early return path is unchanged (line ~140)
- [ ] Cache key (`"all_specs"`) is unchanged
- [ ] `source_model == "user"` downstream contract is preserved (user specs are created separately at lines 263, 301)

## Verification

- `docker compose build backend` — build succeeds with no import or syntax errors
- Structural check: `grep -n 'GRAPH ?g' backend/app/views/service.py` shows the new pattern
- Structural check: `grep -n 'graph_to_model' backend/app/views/service.py` shows the reverse map
- Negative check: `grep -n 'model_ids\[0\]' backend/app/views/service.py` returns no matches (old logic removed)
- Run existing E2E tests to confirm no regressions: `docker compose exec playwright npx playwright test` (or equivalent)

## Observability Impact

- Signals added/changed: The existing `logger.info` message at the end of the function already logs spec count and model count — no change needed
- How a future agent inspects this: Read the SPARQL query string in the function; check `source_model` on returned ViewSpec objects
- Failure state exposed: If a graph IRI doesn't match the expected pattern, `graph_to_model.get()` returns `""` — same behavior as before, but now only for truly unmapped graphs rather than all specs

## Inputs

- `backend/app/views/service.py` — current merged FROM-clause query and `model_ids[0] if len(model_ids) == 1 else ""` logic
- S02-RESEARCH.md — documents the `urn:sempkm:model:{id}:views` convention used in `models/registry.py:45` and `views/service.py:146`

## Expected Output

- `backend/app/views/service.py` — `get_all_view_specs()` uses GRAPH pattern, each ViewSpec has correct `source_model` per its originating model graph
