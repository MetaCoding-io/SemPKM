---
id: T04
parent: S02
milestone: M007
provides:
  - type_filter multi-select UI in mount form with checkbox group populated from type-pills endpoint
  - type_filter CRUD in async mount_router.py (create/update/list/get/preview)
  - type_filter CRUD in sync mount_service.py (create/update/list/get_by_id/get_by_prefix)
  - type_filter summary in mount list cards (e.g. "· 2 types")
key_files:
  - backend/app/vfs/mount_router.py
  - backend/app/vfs/mount_service.py
  - backend/app/templates/browser/_vfs_settings.html
  - frontend/static/js/workspace.js
  - frontend/static/css/workspace.css
key_decisions:
  - Used two-query approach for list_mounts type_filter (separate SELECT for typeFilter triples, merged in Python) instead of GROUP_CONCAT subquery — more portable across SPARQL stores
  - Used GROUP_CONCAT with OPTIONAL for single-mount queries (get_by_id, get_by_prefix) — safe for single-result sets
  - Populated type checkboxes from existing GET /browser/views/type-pills endpoint — no new endpoint needed
patterns_established:
  - Multi-valued RDF predicate round-trip pattern: store as individual triples, read via separate query + Python merge for lists, or GROUP_CONCAT for single-resource queries
observability_surfaces:
  - API response includes type_filter array in mount JSON
  - Mount list cards show type count inline (e.g. "· 2 types")
  - RDF inspection via SELECT on sempkm:typeFilter predicate
duration: ~45min
verification_result: passed
completed_at: 2026-03-16
blocker_discovered: false
---

# T04: Type multi-select UI in mount form

**Full type_filter CRUD and checkbox UI for mount creation/edit, with preview support and round-trip persistence via RDF typeFilter triples.**

## What Happened

Added `type_filter: list[str] | None` to all three Pydantic request models (`MountCreateRequest`, `MountUpdateRequest`, `MountPreviewRequest`) in mount_router.py. Updated async create/update endpoints to store individual `<mount> sempkm:typeFilter <typeIRI>` triples. Updated async list endpoint with a two-query approach: main mount query + separate typeFilter query merged in Python. Updated async `_get_mount_by_id_async` with GROUP_CONCAT for single-mount retrieval.

Mirrored all changes in sync `mount_service.py`: `list_mounts` uses two-query merge, `get_mount_by_id` and `get_mount_by_prefix` use GROUP_CONCAT with OPTIONAL, `create_mount` and `update_mount` include type_filter triples in INSERT DATA.

Added HTML type filter section in `_vfs_settings.html` with a container div populated by JS. Added CSS for `.mount-type-filter-container` with flex-wrap layout and checkbox styling. Updated workspace.js: `initMountForm` fetches types from `/browser/views/type-pills` and renders checkboxes; `collectFormData` collects checked IRIs; `populateEditForm` pre-checks saved types; `resetMountForm` unchecks all; `renderMountList` shows type count in mount card meta line.

## Verification

- `python -m pytest tests/ -v -k vfs` — **21/21 passed** (all existing tests pass)
- Browser: Settings → VFS → type checkboxes visible (Project Shape, Person Shape, Note Shape, Concept Shape, ReviewWidget Shape)
- Browser: Created mount "Test Type Filter" with Person Shape and Note Shape checked → mount card shows "· 2 types"
- Browser: Clicked Edit on saved mount → Person Shape and Note Shape pre-checked, others unchecked
- API: `GET /api/vfs/mounts` returns `type_filter: ["urn:sempkm:model:basic-pkm:Note", "urn:sempkm:model:basic-pkm:Person"]`
- Browser: Preview with type filter → returned filtered count
- Slice verification partial: `python -m pytest tests/test_vfs_scope.py -v` — 21/21 passed

## Diagnostics

- **API inspection:** `GET /api/vfs/mounts` — each mount includes `type_filter` array (or null)
- **RDF inspection:** `SELECT ?mount ?tf FROM <urn:sempkm:mounts> WHERE { ?mount <urn:sempkm:typeFilter> ?tf }`
- **Browser DOM:** `document.querySelectorAll('input[name="mount-type-filter-cb"]:checked')` shows selected types
- **Mount list cards:** Type count shown inline in meta line
- **No new failure modes:** Empty/null type_filter is a no-op

## Deviations

- Used two-query approach for list_mounts instead of SPARQL subquery with GROUP_CONCAT — the OPTIONAL subquery with `FILTER(?mount = ?m || !BOUND(?m))` was complex and less portable across SPARQL 1.1 stores. Two simple queries merged in Python is cleaner.
- Browser testing required copying worktree files to main project due to M007 worktree triplestore lock issue (RepositoryLockedException). This is a pre-existing infrastructure issue, not related to code changes.

## Known Issues

- M007 worktree docker-compose triplestore fails with `RepositoryLockedException` on fresh volumes — a LuceneSail locking issue. Main project stack works fine.

## Files Created/Modified

- `backend/app/vfs/mount_router.py` — added type_filter to Pydantic models, create/update/list/get/preview endpoints
- `backend/app/vfs/mount_service.py` — added type_filter to sync CRUD (list/get_by_id/get_by_prefix/create/update)
- `backend/app/templates/browser/_vfs_settings.html` — added type filter checkbox container
- `frontend/static/js/workspace.js` — type filter fetch, population, collection, edit pre-selection, reset, and list display
- `frontend/static/css/workspace.css` — type filter container styles
