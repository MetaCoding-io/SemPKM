---
estimated_steps: 4
estimated_files: 4
---

# T04: browserVisible field on Mental Model ManifestSchema

**Slice:** S05 — Scheduler, Permissions, Bulk EventStore & browserVisible
**Milestone:** M009

## Description

Add `browserVisible` field (default true) to `ManifestIconDef` so Mental Model types can be hidden from the object browser while remaining queryable via SPARQL and linkable via edges. Expose hidden types via `IconService` and filter them from the object browser and generic view type filter pills.

## Steps

1. Add `browser_visible: bool = Field(default=True, alias="browserVisible")` to `ManifestIconDef` in `backend/app/models/manifest.py`.
2. Add `get_hidden_types(self) -> set[str]` method to `IconService` in `backend/app/services/icons.py`. Iterate `_cache` entries, return type IRIs where the source manifest icon has `browserVisible: false`. This requires extending `_build_cache()` to store the `browserVisible` flag alongside the icon data.
3. In `_handle_by_type()` in `backend/app/browser/workspace.py`, call `icon_service.get_hidden_types()` and exclude those IRIs from the result of `shapes_service.get_types()` before rendering. Also apply the same filter in `backend/app/views/router.py` where generic views call `get_types()` for type filter pills.
4. Write `test_browser_visible.py` — manifest parses `browserVisible: false` correctly, `get_hidden_types()` returns correct set, `_handle_by_type` output excludes hidden types, default true behavior preserved, generic view pills exclude hidden types.

## Must-Haves

- [ ] `ManifestIconDef` accepts `browserVisible` field with true default
- [ ] `IconService.get_hidden_types()` returns correct set from manifest data
- [ ] Object browser (`_handle_by_type`) excludes hidden types
- [ ] Generic view type filter pills exclude hidden types
- [ ] Hidden types remain queryable via SPARQL and linkable via edges (no SPARQL changes)

## Verification

- `cd backend && .venv/bin/pytest tests/test_browser_visible.py -v` — all pass
- `cd backend && .venv/bin/pytest tests/ -v` — full suite, zero regressions
- `grep "browser_visible" backend/app/models/manifest.py` — field present
- `grep "get_hidden_types" backend/app/services/icons.py` — method present

## Observability Impact

- **Logger:** `app.services.models` at DEBUG level logs skipped manifests during `browserVisible` scan.
- **Inspection:** `get_hidden_type_iris(models_dir)` can be called standalone to inspect which types are hidden — returns a plain `set[str]`.
- **Failure shape:** Invalid manifests are silently skipped (logged at DEBUG) — no user-facing error. If a type unexpectedly appears/disappears from the browser, inspect the model's `manifest.yaml` `icons` section for `browserVisible` values.
- **No SPARQL changes:** Hidden types remain fully queryable; only browser nav/type pills are filtered.

## Inputs

- `backend/app/models/manifest.py` — existing `ManifestIconDef` model
- `backend/app/services/icons.py` — existing `IconService` with `_build_cache()`
- `backend/app/browser/workspace.py` — existing `_handle_by_type()` at ~line 110
- `backend/app/views/router.py` — existing generic view endpoints calling `get_types()`

## Expected Output

- `backend/app/models/manifest.py` — modified, `browserVisible` field on `ManifestIconDef`
- `backend/app/services/icons.py` — modified, `get_hidden_types()` method
- `backend/app/browser/workspace.py` — modified, type filtering in `_handle_by_type`
- `backend/app/views/router.py` — modified, type filtering in generic view pills
- `backend/tests/test_browser_visible.py` — new, ~8-10 tests
