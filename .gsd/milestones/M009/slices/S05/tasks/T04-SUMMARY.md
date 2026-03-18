---
id: T04
parent: S05
milestone: M009
provides:
  - browserVisible field on ManifestIconDef with true default
  - get_hidden_type_iris() for resolving hidden types from on-disk manifests
  - Object browser and generic view type pills exclude hidden types
  - ShapesService.get_types() accepts exclude_iris parameter
key_files:
  - backend/app/models/manifest.py
  - backend/app/services/models.py
  - backend/app/services/icons.py
  - backend/app/browser/_helpers.py
  - backend/app/browser/workspace.py
  - backend/app/views/router.py
  - backend/tests/test_browser_visible.py
key_decisions:
  - Hidden type resolution lives in app.services.models.get_hidden_type_iris() as a standalone function rather than an IconService method — avoids coupling to IconService lifecycle and allows synchronous calls without cache
  - _expand_prefix() duplicated in models.py (identical to IconService version) — keeps the hidden-types function self-contained without IconService dependency
patterns_established:
  - get_hidden_types() in browser._helpers wraps get_hidden_type_iris() with the hardcoded models dir — single import for all browser/view routers
  - ShapesService.get_types(exclude_iris=set) pattern for filtering types at the query layer
observability_surfaces:
  - Logger: app.services.models at DEBUG level logs skipped manifests during browserVisible scan
  - Inspection: get_hidden_type_iris(models_dir) callable standalone to check which types are hidden
  - No SPARQL changes — hidden types remain fully queryable and linkable
duration: 10m
verification_result: passed
completed_at: 2026-03-18
blocker_discovered: false
---

# T04: browserVisible field on Mental Model ManifestSchema

**Added browserVisible field (default true) to ManifestIconDef, get_hidden_type_iris() for manifest-driven type hiding, and filtering in object browser and generic view type pills — 22 tests pass**

## What Happened

All implementation was already present on this branch from prior task execution. Verified the complete feature:
- `ManifestIconDef` in `manifest.py` has `browserVisible: bool = True` field
- `get_hidden_type_iris()` in `services/models.py` scans on-disk manifests, expands prefixed type names, and returns IRIs where `browserVisible: False`
- `get_hidden_types()` helper in `browser/_helpers.py` wraps the function with the models directory
- `_handle_by_type()` in `workspace.py` passes `exclude_iris=get_hidden_types()` to `shapes_service.get_types()`
- `workspace()` route also passes the same exclusion set
- `generic_view()` and `type_pills()` in `views/router.py` both call `shapes_service.get_types(exclude_iris=get_hidden_types())`
- `ShapesService.get_types()` accepts `exclude_iris: set[str] | None` and filters types before returning

## Verification

- `pytest tests/test_browser_visible.py -v` — all 22 tests pass (4 manifest parsing, 5 prefix expansion, 7 hidden type resolution, 6 ShapesService filtering)
- `pytest tests/ -v` — 1032 passed, 4 failed (pre-existing SDK import failures in test_bulk_eventstore.py, unrelated)
- `grep "browserVisible" backend/app/models/manifest.py` — field present
- `grep "get_hidden_type" backend/app/services/models.py` — function present
- `grep "get_hidden_types" backend/app/browser/workspace.py` — used in _handle_by_type and workspace
- `grep "get_hidden_types" backend/app/views/router.py` — used in generic_view and type_pills

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `pytest tests/test_browser_visible.py -v` | 0 | ✅ pass | 2.9s |
| 2 | `pytest tests/ -v` (full suite) | 1 | ⚠️ 1032 pass, 4 pre-existing fail | 13.3s |
| 3 | `pytest tests/test_app_scheduler.py -v` | n/a | ⚠️ file not found (pre-existing) | — |
| 4 | `pytest tests/test_sdk_permissions.py -v` | n/a | ⚠️ file not found (pre-existing) | — |
| 5 | `pytest tests/test_bulk_eventstore.py -v` | 1 | ⚠️ 14 pass, 4 fail (SDK import) | 0.2s |

## Diagnostics

- **Logger:** `app.services.models` at DEBUG level logs skipped manifests during `browserVisible` scan
- **Inspection:** Call `get_hidden_type_iris("/app/models")` to see which types are hidden — returns a plain `set[str]`
- **Failure shape:** Invalid manifests silently skipped (DEBUG log). If a type unexpectedly appears/disappears from browser, check the model's `manifest.yaml` icons section for `browserVisible` values.
- **No SPARQL impact:** Hidden types remain queryable via SPARQL and linkable via edges — only browser nav tree and type filter pills are filtered.

## Deviations

None — implementation was already complete on this branch.

## Known Issues

- `test_app_scheduler.py` and `test_sdk_permissions.py` are missing from the worktree (not committed from T01/T02). T01 and T02 summaries confirm they were written and passed during those tasks.
- 4 `TestSDKBulkContextManager` tests in `test_bulk_eventstore.py` fail due to `sempkm_app_sdk` not being installed in the backend venv — pre-existing from T03, not a T04 issue.

## Files Created/Modified

- `backend/app/models/manifest.py` — `browserVisible: bool = True` field on `ManifestIconDef`
- `backend/app/services/models.py` — `get_hidden_type_iris()` and `_expand_prefix()` functions
- `backend/app/services/icons.py` — existing, unchanged (hidden type resolution moved to models.py)
- `backend/app/browser/_helpers.py` — `get_hidden_types()` wrapper function
- `backend/app/browser/workspace.py` — `_handle_by_type()` and `workspace()` pass `exclude_iris` to `get_types()`
- `backend/app/views/router.py` — `generic_view()` and `type_pills()` pass `exclude_iris` to `get_types()`
- `backend/app/services/shapes.py` — `get_types()` accepts `exclude_iris` parameter
- `backend/tests/test_browser_visible.py` — 22 tests covering manifest parsing, prefix expansion, hidden type resolution, and ShapesService filtering
