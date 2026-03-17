---
estimated_steps: 5
estimated_files: 4
---

# T03: browserVisible field and type filtering

**Slice:** S05 — Scheduler, Permissions, Bulk EventStore & browserVisible
**Milestone:** M009

## Description

Apps create internal bookkeeping types (ReadActivity, sync cursors) that clutter the object browser. `browserVisible: false` on Mental Model manifest icon definitions hides these types from the type picker and nav tree while keeping them queryable via SPARQL and linkable via edges. Default is `true` for backward compatibility.

The filter applies in Python (inside `ShapesService.get_types()`) rather than as an RDF triple, since `get_types()` already iterates Python objects.

## Steps

1. **Add `browserVisible` field** to `ManifestIconDef` in `backend/app/models/manifest.py`:
   - `browserVisible: bool = True` — existing manifests without this field remain visible
   - No other changes to the manifest schema

2. **Add `get_hidden_type_iris()` function** to `backend/app/services/models.py`:
   - Iterate all installed model manifests (via `ModelService.list_installed_models()` or equivalent)
   - For each manifest's `icons` list, find entries where `browserVisible == False`
   - Expand prefixed type names (e.g. `bpkm:Note`) against the manifest's `prefixes` dict to get full IRIs
   - Return `set[str]` of full IRIs
   - Return empty set if no models are installed or no icons have `browserVisible: false`
   - This function needs access to the model service or its data — determine the cleanest injection pattern (standalone function accepting models list, or method on ModelService)

3. **Modify `ShapesService.get_types()`** in `backend/app/services/shapes.py`:
   - Add optional `exclude_iris: set[str] | None = None` parameter
   - Filter out any type whose `iri` is in `exclude_iris`
   - Callers that should filter: `_handle_by_type()` in workspace routes, type filter pills endpoint, mount form type multi-select
   - Update at least the primary caller (`_handle_by_type()`) to pass the hidden set. Other callers can be updated too but are lower priority.

4. **Write tests** (`backend/tests/test_browser_visible.py`):
   - `ManifestIconDef` defaults `browserVisible` to `True`
   - `ManifestIconDef(browserVisible=False)` parses correctly
   - `get_hidden_type_iris()` returns correct IRIs for hidden types
   - `get_hidden_type_iris()` returns empty set when no models installed
   - `get_hidden_type_iris()` returns empty set when all icons are visible
   - `get_types()` with `exclude_iris` filters correctly
   - `get_types()` without `exclude_iris` returns all types (backward compat)

5. **Verify**: `cd backend && python -m pytest tests/test_browser_visible.py tests/test_app_manifest.py -v`

## Must-Haves

- [ ] `ManifestIconDef.browserVisible` field exists with default `True`
- [ ] Hidden type IRIs resolved from manifest prefixes correctly
- [ ] `get_types()` filters out hidden types when exclude set provided
- [ ] No crash when no models installed (empty set returned)
- [ ] Existing manifest tests still pass (backward compat)

## Verification

- `cd backend && python -m pytest tests/test_browser_visible.py -v` — all pass
- `cd backend && python -m pytest tests/test_app_manifest.py -v` — no regressions (Mental Model manifest, not app manifest — but verify both if app manifest tests exist)

## Inputs

- `backend/app/models/manifest.py` — `ManifestIconDef` class (currently has `type`, `icon`, `color`, `tree`, `graph`, `tab` fields)
- `backend/app/services/shapes.py` — `ShapesService.get_types()` returns `list[dict]` with `iri` and `label` keys
- `backend/app/services/models.py` — model service with installed model access

## Expected Output

- `backend/app/models/manifest.py` — `ManifestIconDef` with `browserVisible: bool = True`
- `backend/app/services/models.py` — `get_hidden_type_iris()` function
- `backend/app/services/shapes.py` — `get_types()` with `exclude_iris` filtering
- `backend/tests/test_browser_visible.py` — ~5-8 tests covering field, resolution, and filtering
