---
id: T03
parent: S05
milestone: M009
provides:
  - ManifestIconDef.browserVisible field with default True
  - get_hidden_type_iris() standalone function for collecting hidden type IRIs from disk manifests
  - ShapesService.get_types(exclude_iris=) filtering parameter
  - Browser-facing routes pass hidden set to get_types() calls
key_files:
  - backend/app/models/manifest.py
  - backend/app/services/models.py
  - backend/app/services/shapes.py
  - backend/app/browser/_helpers.py
  - backend/tests/test_browser_visible.py
key_decisions:
  - get_hidden_type_iris() is a standalone function reading from disk (not async, no triplestore dependency) — mirrors IconService pattern
  - _expand_prefix() duplicated from IconService as a module-level function in models.py to avoid cross-service coupling
  - Filtering applied at all browser-facing get_types() call sites (workspace, objects, pages, views) via get_hidden_types() helper in _helpers.py
patterns_established:
  - browserVisible manifest field pattern: static field on ManifestIconDef, read from disk at request time, no RDF storage
  - get_hidden_types() helper in _helpers.py centralizes models dir path and get_hidden_type_iris() call for browser routes
observability_surfaces:
  - get_hidden_type_iris() logs at DEBUG when skipping bad manifests; safe failure mode (unknown prefix returns original string, won't match any shape IRI)
duration: ~15 min
verification_result: passed
completed_at: 2026-03-16
blocker_discovered: false
---

# T03: browserVisible field and type filtering

**Added `browserVisible: false` support on manifest icon definitions to hide internal types from the object browser while keeping them queryable via SPARQL.**

## What Happened

1. Added `browserVisible: bool = True` field to `ManifestIconDef` in `manifest.py`. Existing manifests without the field remain visible (backward compat via default).

2. Added `get_hidden_type_iris(models_dir)` standalone function and `_expand_prefix()` helper to `models.py`. Iterates on-disk model manifests, finds icons with `browserVisible=False`, expands prefixed type names against manifest `prefixes` dict, returns `set[str]` of full IRIs. Returns empty set for all edge cases (no dir, empty dir, no hidden icons, bad manifests).

3. Modified `ShapesService.get_types()` in `shapes.py` to accept optional `exclude_iris: set[str] | None = None` parameter. When provided, filters out matching type IRIs from the result list.

4. Added `get_hidden_types()` helper to `browser/_helpers.py` — centralizes the `_MODELS_DIR` path and `get_hidden_type_iris()` call. Updated 6 browser-facing call sites to pass the hidden set:
   - `workspace.py` — `_handle_by_type()` nav tree + `workspace()` main page
   - `objects.py` — type picker dialog
   - `pages.py` — lint dashboard type filter
   - `views/router.py` — view type filter pills (2 endpoints)

5. The `obsidian/router.py` call site was left unfiltered — it's for import mapping where users may need to reference internal types.

## Verification

- `pytest tests/test_browser_visible.py -v` — **22/22 passed** covering:
  - ManifestIconDef field defaults/parsing (4 tests)
  - _expand_prefix() edge cases (5 tests)
  - get_hidden_type_iris() with various scenarios (7 tests)
  - ShapesService.get_types() filtering (6 tests)
- `pytest tests/test_model_refresh.py -v` — **21/21 passed** (no regressions)
- `pytest tests/test_class_creation.py -v` — **51/51 passed** (no regressions)
- All modified files pass `ast.parse()` syntax check

### Slice-Level Verification Status

- `test_browser_visible.py` — ✅ all pass
- `test_bulk_eventstore.py` — not yet created (T02 scope, pending)
- `test_app_permissions.py` — not yet created (T01 scope)
- `test_app_scheduler.py` — not yet created (future task)

## Diagnostics

- Inspect hidden types: `from app.services.models import get_hidden_type_iris; get_hidden_type_iris("/app/models")`
- If a type still appears in the browser nav tree despite `browserVisible: false`, check:
  1. The manifest `icons` entry has `browserVisible: false` (not just missing)
  2. The route handler calls `get_types(exclude_iris=get_hidden_types())`
  3. The prefix in the `type` field matches a key in the manifest's `prefixes` dict

## Deviations

- Updated 6 call sites instead of "at least the primary caller" — all browser-facing endpoints now filter. The obsidian import mapper was intentionally left unfiltered.
- Added `_expand_prefix()` as a standalone function in `models.py` rather than reusing `IconService._expand_prefix()` — avoids coupling between model service and icon service.

## Known Issues

None.

## Files Created/Modified

- `backend/app/models/manifest.py` — added `browserVisible: bool = True` to ManifestIconDef
- `backend/app/services/models.py` — added `_expand_prefix()` and `get_hidden_type_iris()` functions
- `backend/app/services/shapes.py` — added `exclude_iris` parameter to `get_types()`
- `backend/app/browser/_helpers.py` — added `get_hidden_types()` helper, imported `get_hidden_type_iris`
- `backend/app/browser/workspace.py` — updated 2 call sites to pass `exclude_iris`
- `backend/app/browser/objects.py` — updated type picker call site
- `backend/app/browser/pages.py` — updated lint dashboard call site
- `backend/app/views/router.py` — updated 2 view filter pill call sites
- `backend/tests/test_browser_visible.py` — 22 tests covering field, resolution, and filtering
